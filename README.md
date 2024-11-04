

# FFpie

an FFmpeg emulator built on PyAV that aims to mimic FFmpeg as much as possible.

it provides:

1. rich and friendly interfaces and toolkits.

2. FFmpeg transplantation of components, e.g. concat demuxer, frames sampling, etc.

3. simple modern modular design.


1.0 is based on PyAV-13.0.0 and FFmpeg-n6.1.1, but you should apply the patch to PyAV in the `patch` directory first, then
build your own PyAV from the source.

and you can download FFmpeg-n6.1.1 from [here.](https://github.com/BtbN/FFmpeg-Builds/releases/)

# motivation

in some cases, just mere interfaces exposed to python are not enough for us, and there are some key pices missing to run
your code to process a video file as FFmpeg.

e.g. by PyAV, you can easily push decoded frames to a graph, and pull filtered frames from the graph, but when frames come
out the other end, they probably won't go immediately into the encoder in FFmpeg, they will be "sampled" before encoding!

you can imagine that there is a sampler conceptually standing in between your graph and the encoder, and it decides which frame
should be sent to the encoder, some frames might be dropped or duplicated in certain sampling policy, or as known as fps_mode.

so when you speed up or slow down your video, you might have to simple the frames yourself.

here we implement the cfr fps_mode in python, and in some cases, cfr is all you need, then you can just take it and make
life easier.

here is another example.

in real life, this is generic that we would run graphs in a cluster of GPU machines, and you have to store the graph and upload
it to the cloud, the graph might be a very big and large piece of plain text, sometimes that long length won't bother you,
but sometimes it matters.

here we introduce graph serialization to help you reduce the size, you can just serialize your graph to a short bytes array, and
deserialize and run the graph anywhere, and take one step further, you can even say compress the serilaized bytes into a
token string that is much shorter than the serialized string.

and to help you understand how FFmpeg works better, we break down FFmpeg video processing into three to four stages, and
then we bridge those gaps between mere interfaces exposion and process flow integrity for you.

simply put, FFpie is an augment wrap to PyAV to enable you take advantage of full or a subset of FFmpeg programmatically.

# usage

(more in the `examples` directory)

when trasncode your video, you can pass in your own encoder to do something before and after encoding a frame.

here an encoder is more than just a "pure" encoder, we will pass the frames out of your graph, or from decoder if no graph,
into your encoder, then you can do anything before and after encoding.

`ffpie.H264Encoder` is a built-in encoder that is capable of labeling a frame as keyframe every N frames before encoding.

and force_id feature is added as a solo plugin at `ffpie.encoder.utils`, which means you can adopt it without introducing
other pieces of code.

```python

import ffpie

s = ffpie.Source(path_to_your_video)
codec_conf = ffpie.NVENCConf.get_default(width=s.width, height=s.height, framerate=s.frame_rate)
print(codec_conf.get_conf_params())
encoder = ffpie.H264Encoder(codec_conf)
# s.seek(10, 20.1)  # seek!
# we want one keyframe per 45 frames.
encoder.forced_idr_frames(45)
# you employ OutContainer to do trivial things for you, such as encoding frames and muxing packets.
with ffpie.OutContainer("oc_with_encoder.mp4",
                        codec_conf=codec_conf,
                        video_encoder=encoder,  
                        ) as oc:
    for idx, frame in enumerate(s.read_video_frames()):
        oc.mux_one_video_frame(frame)
    oc.flush_video()
s.close()

```
if you do not specify an encoder for your output container by leaving the parameter `video_encoder` alone, then oc will use the
default video stream that created by the oc to encode the frames.

you can serialize and deserialize your graph.

```python

import ffpie
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
bytes_data, inputs = g.serialize()
new_g = ffpie.Graph.deserialize(bytes_data)
new_g.setup_inputs(*inputs)
```

speed up your video, and apply the cfr sampler to frames coming out from the graph.

````python

import ffpie

s = ffpie.Source(path_to_your_video)
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

maybe you can't be bothered to anything but just few settings, `ffpie.Clip` comes to help.

```python

import ffpie

s = ffpie.Source(path_to_your_video)
vcodec_conf = ffpie.NVENCConf.get_default(width=s.width, height=s.height)
# you can specify your encoder class/object for your video track,
# or you can just leave encoder_cls as None, just use default encoder that's used by PyAV itself.
vt = ffpie.VideoTrack(input_sources=[s], codec_conf=vcodec_conf, encoder_cls=ffpie.H264Encoder)

# create a mp4 file, and add that your video track to it.
my_clip = ffpie.Clip("my_clip.mp4")
my_clip.add_video_track(vt)
my_clip.run()
```

a clip will do most of the things for you, setting up framerate for the output file, choosing a frames sampler, and whatnot.

# breakdowns on FFmpeg

the following diagram shows the stages into which we can divide FFmpeg processing flow.

```


video1 ===> deocder ===> frames 
video2 ===> deocder ===> frames   ====>  graph(filtering) ====> sampler ===> encoder ===> packets
video3 ===> decoder ===> frames 
...

```

one or multiple collections of frames are being decoded from input videos, and then going into the graph,
and then filtered frames out from the graph will be put into the sampler that will drop or duplicate frames, and then frames
will finally be encoded by the encoder.

as you can see, the flow is quite easy to understand, and PyAV offers a good code expose and wrapping so that you can directly
access FFmpeg functions and structures, which is amazing considering how complated FFmpeg is. 

but it's noteworthy that this is incomplete.

PyAV is not a full copy of FFmpeg, it gives you the ability of passing objects into FFmpeg functions, and calling those functions,
and getting data back.

but in some cases that is not enough if you want to ensure your code run exactly, or as close as FFmpeg.

why don't we just expoe everything?

it is too difficult and, from our opinions, unnecessary, and exposing everything will be equivalent of using FFmpeg command line.

that's hard partly because there is no such a clear delineation between two adjacent stages, and there are not two, maybe
three functions that you can just call then get the results, like calling three functions after a frame out of a graph to do
the sampling.

no, there are actually code snippets scattered in code base together, and each of them is going more than one thing, and dealing
with many edge conditions.

but let's look at this in this way, it is the fact that in many cases, we only need a subset of those features.

here is an example.

a graph has to be configured before enqueuing and dequeuing frames. and you can call the configure method on that graph in PyAV.

it's true that FFmpeg will call that method as well, but FFmpeg also do some extra pieces of work.

e.g. it will insert one more filter before the buffersink/abuffersink, that filter is called format or aformat depending on the
type of your sink filter.

bascially a format, or aformt filter does is just transformat the frames to the default video or audio frame format, which
are yuv420p and fltp respectively.

and obviously, this is actually a trivial operation because when you build or form your graph you know what you are doing, you
have your graph in mind, and know what your graph exactly looks like.

so we do not have to copy-paste such thing, and the cfr sampler that we have mentioned is another good example.

the fps_mode implementation in FFmpeg involves many steps, it has to consider all four policies that FFmpeg supports.

in our case, at least for now, cfr is one that we only need, and cfr is also one of those basic policies, and is incorporated

into many products, cfr is must-have to people.

we can pluck the cfr sampler from FFmpeg without exposing every piece of code, if we get the underlying idea by

analyzing its source code.

and you can find that analysis on `docs/how_FFmpeg_speeds_up_a_video.md`, there we trace the invoking chain to the bottom to

unveil how FFmpeg works by the example of speeding up a video.

## clips

when you get the packets out of the encoder, you can write them into a container, whether it is a mp4 file, or an avi, or
some other format, here we call it a clip.

of course, a container has more than just packets including other metadata, but here this is rather a conceptual abstraction.

simply put, a container, or a clip contains the packets encoded by an encoder, two clips are the same if and only if they
have the same set of components, the graph, and the sampler, and the encoder with specific configuration, and the input videos.

it can be a video clip that holds only video packets, or an audio clip that has only audio bytes inside, or a mixed clip.

by the way, one of the differences lies between video editing and video sharing platforms such as YouTube is that you do not
pre-transocode your original video, in our opinions, because transocding a sequence of frames means you want to stitch them and
other frames together.

e.g. if you just want the frames from 10s to 20s, why transocde the entire video?

## tracks and concatenation

maybe, a single clip is what you want since a clip is also a video file, like transcoding a video, or cutting a portion of
the video and rotating frames, etc.

but often to get the video you want, you have to concatenate multiple clips, more specifically, you are chaining the video
packets in each clip one by one from left to right, and chaining audio packets in those clips one by one.

remember when taking about clips, videos, we are talking about manipulating the tracks, or the streams in PyAV.

```

                                                        video
video = clip1 + clip2 + clip3,...  ====>     video track:   clip1, clip2, clip3, ...
                                             audio track:   clip1, clip2, clip3, ...



```

and FFmpeg introduces an approach named concat demuxer, and how FFmpeg implements concat demuxing is described in
`docs/ffmpeg_concat_demuxer.md`.

and what's important to keep in mind is that your video will display correctly from left to right starting at time 0 when
linking multiple clips.

but it will go wrong when you jump into another time point, e.g. you might get glitches when you fast-forward/backward you
video, if you did not encode them with the same configuration.


# TODO

1. translate FFmpeg filter_complex strings to a Graph object.

2. VPF integration.
