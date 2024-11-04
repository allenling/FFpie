

import dataclasses

from .abs import VideoFilter


@dataclasses.dataclass
class Split(VideoFilter):
    fname = "split"
    nick_name = "spl"
    outputs_count = 2



def main():
    return


if __name__ == "__main__":
    main()
