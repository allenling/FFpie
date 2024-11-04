

import dataclasses

from .abs import VideoFilter


@dataclasses.dataclass
class VFlip(VideoFilter):
    fname = "vflip"
    nick_name = "vf"


@dataclasses.dataclass
class HFlip(VideoFilter):
    fname = "hflip"
    nick_name = "hf"




def main():
    return


if __name__ == "__main__":
    main()
