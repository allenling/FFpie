


import dataclasses

from .abs import VideoFilter


@dataclasses.dataclass
class BufferSink(VideoFilter):
    fname = "buffersink"
    nick_name = "bus"




def main():
    return


if __name__ == "__main__":
    main()
