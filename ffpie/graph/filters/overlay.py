

import dataclasses

from .abs import VideoFilter


@dataclasses.dataclass
class Overlay(VideoFilter):
    fname = "overlay"
    nick_name = "ovl"
    inputs_count = 2


def main():
    return


if __name__ == "__main__":
    main()
