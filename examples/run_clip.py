
import ffpie


FPATH = r"D:\Downloads\yellowstone.mp4"


def build_video_track():
    s1 = ffpie.Source(FPATH)
    vcodec_conf = ffpie.NVENCConf.get_default(width=s1.width, height=s1.height)
    vg = ffpie.Graph()
    vg.link_filters(ffpie.Setpts(speed=2))
    vt = ffpie.VideoTrack(input_sources=[s1], codec_conf=vcodec_conf, encoder_cls=ffpie.H264Encoder, g=vg)
    return vt


def build_audio_track():
    s2 = ffpie.Source(FPATH)
    ag = ffpie.Graph()
    ag.link_filters(ffpie.Atempo(speed=2))
    at = ffpie.AudioTrack(input_sources=[s2], codec_conf=ffpie.AACConf(), g=ag)
    return at


def edit_a_clip():
    #
    my_clip = ffpie.Clip("my_clip.mp4")
    my_clip.add_video_track(build_video_track())
    my_clip.add_audio_track(build_audio_track())
    my_clip.run()
    return


def main():
    edit_a_clip()
    return


if __name__ == "__main__":
    main()
