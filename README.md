

# FFpie

an FFmpeg emulator that aims to mimic FFmpeg as much as possible.

FFpie is built on top of PyAV and provides:

1. rich and user-friendly interfaces and tools more than simply exposing C code.

2. simpler Python implementation of FFmpeg features, including mimicry of FFmpeg workflow, concat demuxer, video sync sampling, etc.

3. simple and modern modular design gives better observability.

# Motivation

FFmpeg is probably one of the most prominent media processing applications in the world, it's fast and easy to use as a command line tool.

and FFmpeg is also complex in terms of readability, which imposes a heavy mental cognative load on people using it.

and FFmpeg is written mostly by C/C++, that makes delving into the code base very daunting for many developers.

here is where PyAV comes to help.

PyAV is a Pythonic binding for the FFmpeg libraries, that means PyAV exposes FFmpeg C code to Python making it easier to use. 

you can write Python code that calls back and forth from and to FFmpeg C or C++ code natively at any point.

PyAV does not offer a full and complete Python warpping of FFmpeg C code, and this is not required in order to use FFmpeg to
run most media processing tasks.

PyAV is a great and excellent tool making running FFmpeg in your Python code possible and simple rather than just running FFmpeg as a
command line tool in another process.

but in its heart, PyAV is still just a sort of Python version of FFmpeg, you have to be familiar with FFmpeg to some extent to use
PyAV effectively and efficiently.

e.g. typically in FFmpeg workflow, you will run your filters on the input frames, and then before going to push those output
frames into your encoder, FFmpeg will sample the frames to adjust dts and pts.

this is called video sync method or framerate mode, and we just call it pre-encoding sampling.

you can tell FFmepeg to use different mode or method via `fps_mode` param to sample those frames to be encoding, the default option
is called cfr, Constant Frame Rate.

and this is omitted in PyAV, so in some cases, e.g. speed up a video file, you would find that there are some unexpected discrepancies
in video quality and fps between the video file output by PyAV and the one processed by FFmpeg command line tool.

and why PyAV has not exposed this?

mainly because that that video sync method is hard to extract from FFmpeg, it's not just a few lines of code, or a few classes and
objects.

that smapling process is embedded into a couple of places, and you have to have a clear grasp of how that sampling runs, and carefully
pluck off particular lines of code.

and even though you had wrapped those C functions and exposed them to Python, you probably still had to explain how to combine those
functions together, and what parameters would be used for which scenario in order to apply that sampling process to your frames.

this is not what PyAV for, PyAV is built for pure code exposing.

that's the pain for the adoption of FFmpeg for at least us. 

so we take a step further, we decided to re-implement a couple of FFmpeg features in Python so that you do not have to get into the
weeds and understand what's happening inside FFmpeg in order to adopt FFmpeg into your application.

one of the goals of building FFpie is to make FFmpeg into a very simple piece of software that you can go and write, and we handle
all of the complexity, or the undifferentiated problems of handling media processing in an app.

# Requiremenets. 

now FFpie is based on PyAV-13.0.0 and FFmpeg-n6.1.1, and you have to apply patches in `patches` directory before building PyAV from source.

you can download FFmpeg-n6.1.1 binary file from [here.](https://github.com/BtbN/FFmpeg-Builds/releases/)

# Usage

open your video file, seek to a certain position, force idr, and encode the video frames, and write into the output file.

```python

import ffpie

s = ffpie.Source("/path/to/your/video.mp4")
codec_config = ffpie.NVENCConf.get_default(width=s.width, height=s.height, framerate=s.frame_rate)
print(codec_config.get_conf_params())
encoder = ffpie.H264Encoder(codec_config)
# s.seek(10, 20.1)  # seek!
# we want one keyframe per 45 frames.
encoder.forced_idr_frames(45)
# OutContainer would trivial things for you, such as encoding frames and muxing packets.
with ffpie.OutContainer("oc_with_encoder.mp4",
                        codec_conf=codec_config,
                        video_encoder=encoder,  
                        ) as oc:
    for idx, frame in enumerate(s.read_video_frames()):
        oc.mux_one_video_frame(frame)
    oc.flush_video()
s.close()

```

link your filters in an intutive fashion.

create edges of your graph first, and then connect the head to the tail.

```python

import os
import cv2 as cv
import ffpie


def build_and_run_graph():
    """
                   branc1          branc2                               brach4
        x.mp4  -->  split --> scale --> hflip ------>  hstack ---> overlay --> hflip --> output
                     |                                  ^             ^
                     |                                  |             |
                     +-----> scale --> vflip -----------+            png
                           branch3

    """
    v1_path = r"x.mp4"
    v2_path = r"y.mp4"
    v3_path = r"z.png"
    s1 = ffpie.Source(v1_path)
    s2 = ffpie.Source(v2_path)
    lay_s = ffpie.ImageReader(v3_path)
    v1 = ffpie.Buffer(template=s1.video_stream)
    v2 = ffpie.Buffer(template=s2.video_stream)
    v3 = ffpie.Buffer(template=lay_s.stream)
    #
    g = ffpie.Graph(v1, v3)
    # build branches first
    b1_start, b1_end = g.link_filters(ffpie.Split())
    b2_start, b2_end = g.link_filters(ffpie.Scale(width="iw/2", height="ih"), ffpie.HFlip())
    b3_start, b3_end = g.link_filters(ffpie.Scale(width="iw/2", height="ih"), ffpie.VFlip())
    b4_start, b4_end = g.link_filters(ffpie.HStack(), ffpie.Overlay(), ffpie.HFlip())
    g.link(b1_end, b2_start, 0, 0)
    g.link(b1_end, b3_start, 1, 0)
    g.link(b2_end, b4_start, 0, 0)
    g.link(b3_end, b4_start, 0, 1)
    #
    g.nb_threads = os.cpu_count()
    print("graph nb_threads", g.nb_threads)
    for f1, f2 in zip(s1.read_video_frames(), lay_s.read_video_frames()):
        outframe = g.apply_frames(f1, f2)[0]
        cv_frame = outframe.to_ndarray(format='bgr24')
        cv.imshow("12", cv_frame)
        cv.waitKey(1)
    lay_s.close()
    s1.close()
    s2.close()
    return
```

sample the frames out from your graph before encoding.

you can use that standalone CFR sampler independently.

````python

import ffpie

s = ffpie.Source("/path/to/your/video.mp4")
# we will link buffers and buffersinks for you when apply_frames being called, callling g.configure is an option.
g = ffpie.Graph(ffpie.Buffer(template=s.video_stream))
# link filters one by one in link_filters method.
g.link_filters(ffpie.Setpts(speed=2))
#
codec_conf = ffpie.NVENCConf.get_default(width=s.width, height=s.height,
                                         framerate=s.frame_rate,
                                         )
print(codec_conf.get_conf_params())
encoder = ffpie.H264Encoder(codec_conf)
# here we specify the fps of the output file to be the same as the input file.
frm = ffpie.CFRSampler(out_fps=codec_conf.framerate)
with ffpie.OutContainer("speed_video.mp4",
                        codec_conf=codec_conf,
                        video_encoder=encoder) as oc:
    for idx, frame in enumerate(s.read_video_frames()):
        outframe = g.apply_frames(frame)[0]
        for rframe in frm.sample(outframe):
            oc.mux_one_video_frame(rframe)
    frm.flush_to_oc(oc)
    oc.flush_video()
s.close()
````

maybe you can't be bothered to do all those trivial things, use `ffpie.Clip`.

`Clip` will do all the things for you, all you have to do pass in your options.

```python

import ffpie

s = ffpie.Source("/path/to/your/video.mp4")
vcodec_conf = ffpie.NVENCConf.get_default(width=s.width, height=s.height)
vt = ffpie.VideoTrack(input_sources=[s], codec_conf=vcodec_conf, encoder_cls=ffpie.H264Encoder)

my_clip = ffpie.Clip("my_clip.mp4")  # output file path.
my_clip.add_video_track(vt)
my_clip.run()
```

maybe in some cases you want to serialize and deserialize your graph.

```python

import cv2 as cv

import ffpie

from ffpie.graph.token import RedisToken


def graph_serialization():
   v1_path = r"D:\Downloads\yellowstone.mp4"
   v2_path = r"D:\Downloads\yosemiteA.mp4"
   v3_path = r"D:\Downloads\73602_85f0a86824d34462bb728c.png"
   s1 = ffpie.Source(v1_path)
   s2 = ffpie.Source(v2_path)
   lay_s = ffpie.ImageReader(v3_path)
   v1 = ffpie.Buffer(template=s1.video_stream, name="v1")
   v2 = ffpie.Buffer(template=s2.video_stream, name="v2")
   v3 = ffpie.Buffer(template=lay_s.stream, name="v3")
   #
   g = ffpie.Graph(v1, v3)
   b1_start, b1_end = g.link_filters(ffpie.Split(name="s1"))
   b2_start, b2_end = g.link_filters(ffpie.Scale(width="iw/2", height="ih"), ffpie.HFlip())
   b3_start, b3_end = g.link_filters(ffpie.Scale(width="iw/2", height="ih"), ffpie.VFlip())
   b4_start, b4_end = g.link_filters(ffpie.HStack(), ffpie.Overlay(name="o1"), ffpie.HFlip())
   g.link(b1_end, b2_start, 0, 0)
   g.link(b1_end, b3_start, 1, 0)
   g.link(b2_end, b4_start, 0, 0)
   g.link(b3_end, b4_start, 0, 1)
   #
   bytes1, leaves1 = g.serialize()
   print(bytes1)
   print(leaves1)
   g.mark_input_output()
   bytes2, leaves2 = g.serialize()
   print(bytes2)
   print(leaves2)
   print(bytes1 == bytes2)
   inputs = [v1, v2, v3]
   inputs_map = {}
   for i in inputs:
      inputs_map[i.name] = i
   preorder_inputs = []
   for fname, _ in leaves2:
      preorder_inputs.append(inputs_map[fname])
   print(preorder_inputs)
   new_g = ffpie.Graph.deserialize(bytes2)
   bytes3, leaves3 = new_g.serialize()
   print(bytes3)
   print(leaves3)
   print(bytes1 == bytes3)
   new_g.set_inputs(*preorder_inputs)
   bytes4, leaves4 = new_g.serialize()
   print(bytes4)
   print(leaves4)
   print(bytes1 == bytes4)
   #
   redis_token = RedisToken()
   redis_token.con.delete(redis_token.chunk_zset_key)
   redis_token.con.delete(redis_token.chunk_amount_key)
   bytes5, leaves5 = new_g.serialize()
   token1 = redis_token.get_token(bytes5)
   print(token1)
   print(leaves5)
   print(bytes1 == bytes5)
   #
   bytes6 = redis_token.from_token(token1)
   tg = ffpie.Graph.deserialize(bytes6)
   bytes7, leaves7 = tg.serialize()
   print(bytes7)
   print(leaves7)
   print(bytes1 == bytes7)
   tg.set_inputs(*preorder_inputs)
   #
   for f1, f2 in zip(s1.read_video_frames(), lay_s.read_video_frames()):
      outframe = tg.apply_frames(f1, f2)[0]
      cv_frame = outframe.to_ndarray(format='bgr24')
      cv.imshow("12", cv_frame)
      cv.waitKey(1)
   s1.close()
   lay_s.close()
   return

```

# Implementation details

for more details on implementation, check out implementation.md

