

import dataclasses

from .abs import VideoFilter


@dataclasses.dataclass
class HStack(VideoFilter):
    fname = "hstack"
    nick_name = "hst"
    inputs_count = 2



def main():
    return


if __name__ == "__main__":
    main()
