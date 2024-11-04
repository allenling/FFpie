



import os

import fractions

import cv2 as cv


import ffpie

FPATH = r"D:\Downloads\yellowstone.mp4"


def scale_and_vflip():
    s = ffpie.Source(FPATH)
    g = ffpie.Graph()
    filters = [ffpie.Scale(width="iw/2", height="ih/2"), ffpie.VFlip()]
    head_idx, tail_idx = g.link_filters(*filters)
    g.add_input_template(head_idx, s.video_stream)
    g.add_output(tail_idx)
    for frame in s.read_video_frames():
        # apply_frames will call the configure method
        outframe = g.apply_frames(frame)[0]
        cv_frame = outframe.to_ndarray(format='bgr24')
        cv.imshow("12", cv_frame)
        cv.waitKey(1)
    s.close()
    return


def run_graph_and_encode():
    s = ffpie.Source(FPATH)
    g = ffpie.Graph()
    filters = [ffpie.Scale(width="iw/2", height="ih/2"), ffpie.VFlip()]
    g.link_filters(*filters)
    # specify inputs in configure, and let graph decide the outputs
    g.configure(ffpie.Buffer(template=s.video_stream))
    #
    codec_conf = ffpie.NVENCConf.get_default(width=s.width//2, height=s.height//2,
                                             framerate=fractions.Fraction(30, 1),
                                             )
    encoder = ffpie.H264Encoder(codec_conf)
    print(codec_conf.get_conf_params())
    with ffpie.OutContainer("graph_encode.mp4",
                            codec_conf=codec_conf,
                            video_encoder=encoder) as oc:
        oc.add_stream(codec_conf)
        for idx, frame in enumerate(s.read_video_frames()):
            outframe = g.apply_frames(frame)[0]
            oc.mux_one_video_frame(outframe)
        oc.flush_video()
    s.close()
    return


def run_complicated_graph():
    """
                 branc1          branc2                       brach4
        mp4  -->  split --> scale --> hflip ------>  hstack ---> overlay --> hflip --> output
                    |                                ^             ^
                    |                                |             |
                    +-----> scale --> vflip ---------+            png
                           branch3

    """
    v1_path = r"D:\Downloads\yellowstone.mp4"
    v2_path = r"D:\Downloads\yosemiteA.mp4"
    v3_path = r"D:\Downloads\73602_85f0a86824d34462bb728c.png"
    s1 = ffpie.Source(v1_path)
    s2 = ffpie.Source(v2_path)
    lay_s = ffpie.ImageReader(v3_path)
    v1 = ffpie.Buffer(template=s1.video_stream)
    v2 = ffpie.Buffer(template=s2.video_stream)
    v3 = ffpie.Buffer(template=lay_s.stream)
    #
    """
    specify inputs by the order of being added into the graph.
    it means v1 will point to the first leave, and v3 will point to the second leave.
    and here, the first leave is going to be the split filter, which has only one input.
    and the second leave is going to be the second input of the overlay filter.
         v1 --> 0.split
     hstack --> 0.overlay
         v3 --> 1.overlay
    this is a convenient way to initialize your graph if you know what your graph structure is.
    """
    g = ffpie.Graph(v1, v3)
    b1_start, b1_end = g.link_filters(ffpie.Split())
    b2_start, b2_end = g.link_filters(ffpie.Scale(width="iw/2", height="ih"), ffpie.HFlip())
    b3_start, b3_end = g.link_filters(ffpie.Scale(width="iw/2", height="ih"), ffpie.VFlip())
    b4_start, b4_end = g.link_filters(ffpie.HStack(), ffpie.Overlay(), ffpie.HFlip())
    g.link(b1_end, b2_start, 0, 0)
    g.link(b1_end, b3_start, 1, 0)
    g.link(b2_end, b4_start, 0, 0)
    g.link(b3_end, b4_start, 0, 1)
    #
    print("graph nb_threads", g.nb_threads)
    g.nb_threads = os.cpu_count()
    for f1, f2 in zip(s1.read_video_frames(), lay_s.read_video_frames()):
        outframe = g.apply_frames(f1, f2)[0]
        cv_frame = outframe.to_ndarray(format='bgr24')
        cv.imshow("12", cv_frame)
        cv.waitKey(1)
    lay_s.close()
    s1.close()
    s2.close()
    return


def main():
    # scale_and_vflip()
    # run_graph_and_encode()
    run_complicated_graph()
    return


if __name__ == "__main__":
    main()
