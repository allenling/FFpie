


import av


def read_packets():
    fpath = r"D:/Downloads/yellowstone.mp4"
    # fpath = r"../examples/transcode_video_frames.mp4"
    # fpath = r"../examples/oc_with_encoder.mp4"
    # fpath = r"../examples/transcode_video_frames.mp4"
    # fpath = r"../examples/transcode_video_frames1.mp4"
    fpath = r"../examples/f1.mp4"
    # fpath = r"../examples/remux_transcodings.mp4"
    f = av.open(fpath)
    print(fpath, f.duration)
    if f.streams.video:
        last_packet = None
        for idx, packet in enumerate(f.demux(video=0)):
            if packet.dts is None:
                break
            print(packet, packet.duration, packet.time_base, float(packet.dts*packet.time_base), float(packet.pts*packet.time_base))
            # if idx >= 100:
            #     break
            if last_packet is None or packet.pts > last_packet.pts:
                last_packet = packet
        print(f.streams.video[0].duration, f.streams.video[0].time_base)
        print(last_packet, last_packet.duration, float(last_packet.pts * packet.time_base))
        print("=============")
    if f.streams.audio:
        f.seek(0)
        for idx, packet in enumerate(f.demux(audio=0)):
            if packet.dts is None:
                break
            print(packet, packet.duration, packet.time_base, float(packet.dts*packet.time_base), float(packet.pts*packet.time_base))
        print(f.streams.audio[0].duration, f.streams.audio[0].time_base, float(f.streams.audio[0].duration*f.streams.audio[0].time_base))
        print("=============")
    return


def main():
    read_packets()
    return


if __name__ == "__main__":
    main()
