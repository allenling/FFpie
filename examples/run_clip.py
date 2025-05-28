
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


def get_complicated_graph():
    v1_path = r"D:\Downloads\yellowstone.mp4"
    v2_path = r"D:\Downloads\yosemiteA.mp4"
    v3_path = r"D:\Downloads\73602_85f0a86824d34462bb728c.png"
    s1 = ffpie.Source(v1_path)
    s2 = ffpie.Source(v2_path)
    s3 = ffpie.ImageReader(v3_path)
    #
    g = ffpie.Graph()
    b1_start, b1_end = g.link_filters(ffpie.Split())
    b2_start, b2_end = g.link_filters(ffpie.Scale(width="iw/2", height="ih"), ffpie.HFlip())
    b3_start, b3_end = g.link_filters(ffpie.Scale(width="iw/2", height="ih"), ffpie.VFlip())
    b4_start, b4_end = g.link_filters(ffpie.HStack(), ffpie.Overlay(), ffpie.HFlip())
    #
    g.link(b1_end, b2_start, 0, 0)
    g.link(b1_end, b3_start, 1, 0)
    g.link(b2_end, b4_start, 0, 0)
    g.link(b3_end, b4_start, 0, 1)
    return s1, s2, s3, g


def complicated_graph():
    #
    s1, s2, s3, g = get_complicated_graph()
    codec_conf = ffpie.NVENCConf.get_default()
    vt = ffpie.VideoTrack(input_sources=[s1, s3], codec_conf=codec_conf, g=g)
    clip = ffpie.Clip("complicated_graph_clip.mp4")
    clip.add_video_track(vt)
    clip.run()
    return


def get_clip_packets():
    s1, s2, s3, g = get_complicated_graph()
    codec_conf = ffpie.NVENCConf.get_default()
    encoder_cls = ffpie.H264Encoder
    vt = ffpie.VideoTrack(input_sources=[s1, s3], codec_conf=codec_conf, encoder_cls=encoder_cls, g=g)
    clip = ffpie.Clip()
    clip.add_video_track(vt)
    with ffpie.OutContainer("clip_packets.mp4") as oc:
        packets = clip.gen_video_packets()
        packet = next(packets)
        oc.add_stream(codec_conf=codec_conf)
        oc.mux_one_video(packet)
        for packet in packets:
            oc.mux_one_video(packet)
    return


def main():
    # edit_a_clip()
    # complicated_graph()
    get_clip_packets()
    return


if __name__ == "__main__":
    main()
