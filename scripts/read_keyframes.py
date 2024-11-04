


import av


def read():
    # fpath = r"../examples/encode_by_encoder.mp4"
    # fpath = r"../examples/encode_by_stream.mp4"
    fpath = r"../examples/transcode_video_frames1.mp4"
    fpath = r"d:\Downloads\yellowstone.mp4"
    f = av.open(fpath)
    for idx, frame in enumerate(f.decode(audio=0)):
        print(frame, frame.pts, frame.time_base)
        if idx >= 100:
            break
    return


def main():
    read()
    return


if __name__ == "__main__":
    main()
