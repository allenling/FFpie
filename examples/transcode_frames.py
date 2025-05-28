

import ffpie


FPATH = r"D:\Downloads\yellowstone.mp4"



def transcode_video_frames():
    s = ffpie.Source(FPATH)
    codec_conf = ffpie.NVENCConf.get_default(width=s.width, height=s.height,
                                             framerate=s.frame_rate,
                                             )
    print(codec_conf.get_conf_params())
    encoder = ffpie.H264Encoder(codec_conf)
    oc = ffpie.OutContainer("transcode_video_frames.mp4")
    oc.add_stream(codec_conf)
    for idx, frame in enumerate(s.read_video_frames()):
        for packet in encoder.encode(frame):
            oc.mux_one_video(packet)
    for packet in encoder.encode(None):
        oc.mux_one_video(packet)
    oc.close()
    s.close()
    return


def transcode_audio_frames():
    s = ffpie.Source(FPATH)
    codec_conf = ffpie.AACConf()
    print(codec_conf.get_conf_params())
    encoder = ffpie.AACEncoder(codec_conf)
    with ffpie.OutContainer("transcode_audio_frames.mp4") as oc:
        oc.add_stream(codec_conf)
        for idx, frame in enumerate(s.read_audio_frames()):
            for packet in encoder.encode(frame):
                oc.mux_one_audio(packet)
        for packet in encoder.encode(None):
            oc.mux_one_audio(packet)
    s.close()
    return


def oc_with_encoder():
    s = ffpie.Source(FPATH)
    codec_conf = ffpie.NVENCConf.get_default(width=s.width, height=s.height,
                                             framerate=s.frame_rate,
                                             )
    print(codec_conf.get_conf_params())
    encoder = ffpie.H264Encoder(codec_conf)
    encoder.forced_idr_frames(45)
    # specify your encoder object in oc
    with ffpie.OutContainer("oc_with_encoder.mp4",
                            codec_conf=codec_conf,
                            video_encoder=encoder,
                            ) as oc:
        for idx, frame in enumerate(s.read_video_frames()):
            oc.mux_one_video_frame(frame)
        oc.flush_video()
    s.close()
    return


def oc_with_stream():
    s = ffpie.Source(FPATH)
    codec_conf = ffpie.NVENCConf.get_default(width=s.width, height=s.height,
                                             framerate=s.frame_rate,
                                             )
    print(codec_conf.get_conf_params())
    # no encoders, so oc will encode the frames with its own codec context in the stream.
    with ffpie.OutContainer("oc_with_stream.mp4", codec_conf=codec_conf) as oc:
        for idx, frame in enumerate(s.read_video_frames()):
            oc.mux_one_video_frame(frame)
        oc.flush_video()
    s.close()
    return


def remux_transcodings():
    video_s = ffpie.Source("transcode_video_frames.mp4")
    audio_s = ffpie.Source("transcode_audio_frames.mp4")
    with ffpie.OutContainer("remux_transcodings.mp4") as oc:
        oc.add_stream(template=video_s.video_stream)
        oc.add_stream(template=audio_s.audio_stream)
        for packet in video_s.read_video_packets():
            oc.mux_one_video(packet)
        for packet in audio_s.read_audio_packets():
            oc.mux_one_audio(packet)
    video_s.close()
    audio_s.close()
    return


def main():
    transcode_video_frames()
    # transcode_audio_frames()
    # oc_with_encoder()
    # oc_with_stream()
    # remux_transcodings()
    return


if __name__ == "__main__":
    main()
