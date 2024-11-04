
import ffpie


FPATH = r"D:\Downloads\yellowstone.mp4"


def sample_audio_frames():
    s = ffpie.Source(FPATH)
    g = ffpie.Graph()
    branch = [ffpie.Atempo(speed=2)]
    first_idx, last_idx = g.link_filters(*branch)
    g.add_input_template(first_idx, s.audio_stream)
    g.add_output(last_idx)
    #
    codec_conf = ffpie.AACConf()
    encoder = ffpie.AACEncoder(codec_conf)
    # fr = ffpie.AudioFramesSampler(min_samples=1024, fmt="fltp", layout="stereo", sample_rate=44100)
    frm = ffpie.AudioCommonSampler(codec_ctx=encoder.codec_ctx)
    with ffpie.OutContainer("sample_audio_frames.mp4", codec_conf=codec_conf,
                            audio_encoder=encoder,
                            ) as oc:
        for idx, frame in enumerate(s.read_audio_frames()):
            outframe = g.apply_frames(frame)[0]
            if not outframe:
                continue
            for rframe in frm.sample(outframe):
                oc.mux_one_audio_frame(rframe)
        frm.flush_to_oc(oc)
        oc.flush_audio()
    s.close()
    return


def sample_video_frames():
    s = ffpie.Source(FPATH)
    g = ffpie.Graph()
    branch = [ffpie.Setpts(speed=2)]
    first_idx, last_idx = g.link_filters(*branch)
    g.add_input_template(first_idx, s.video_stream)
    g.add_output(last_idx)
    g.configure()
    #
    codec_conf = ffpie.NVENCConf.get_default(width=s.width, height=s.height,
                                             framerate=s.frame_rate,
                                             )
    print(codec_conf.get_conf_params())
    encoder = ffpie.H264Encoder(codec_conf)
    frm = ffpie.CFRSampler(codec_conf.framerate)
    with ffpie.OutContainer("sample_video_frames.mp4",
                            codec_conf=codec_conf,
                            video_encoder=encoder) as oc:
        for idx, frame in enumerate(s.read_video_frames()):
            outframe = g.apply_frames(frame)[0]
            for rframe in frm.sample(outframe):
                oc.mux_one_video_frame(rframe)
        frm.flush_to_oc(oc)
        oc.flush_video()
    s.close()
    return


def remux_video_audio():
    video_s = ffpie.Source("sample_video_frames.mp4")
    audio_s = ffpie.Source("sample_audio_frames.mp4")
    with ffpie.OutContainer("remux_video_audio.mp4") as oc:
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
    sample_audio_frames()
    # sample_video_frames()
    # remux_video_audio()
    return


if __name__ == "__main__":
    main()
