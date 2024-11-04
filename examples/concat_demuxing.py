


import ffpie



def transocding(fpath, outpath, start=0, end=None):
    video_s = ffpie.Source(fpath)
    trans_clip = ffpie.Clip(outpath)
    video_s.seek(start=start, end=end)
    codec_conf = ffpie.NVENCConf.get_default(width=video_s.width, height=video_s.height)
    trans_clip.add_video_track(ffpie.VideoTrack(input_sources=[video_s],
                                                codec_conf=codec_conf,
                                                encoder_cls=ffpie.H264Encoder,
                                                ),
                               )
    audio_s = ffpie.Source(fpath)
    audio_s.seek(start=start, end=end)
    trans_clip.add_audio_track(ffpie.AudioTrack(input_sources=[audio_s], codec_conf=ffpie.AACConf()))
    trans_clip.run()
    return ffpie.Source(trans_clip.outpath)


def concat_demuxer():
    f1_path = r"D:\Downloads\yellowstone.mp4"
    f2_path = r"D:\Downloads\yosemiteA.mp4"
    o1 = transocding(f1_path, "f1.mp4")
    o2 = transocding(f2_path, "f2.mp4")
    concat = ffpie.SimpleConcat("concat_demuxer.mp4", sources=[o1, o2])
    concat.demux()
    return


def concat_video_audio():
    s1 = ffpie.Source("transcode_audio_frames.mp4")
    s2 = ffpie.Source("transcode_video_frames.mp4")
    concat = ffpie.SimpleConcat("concat_video_audio.mp4", sources=[s1, s2])
    concat.demux()
    return


def main():
    concat_demuxer()
    # concat_video_audio()
    return


if __name__ == "__main__":
    main()
