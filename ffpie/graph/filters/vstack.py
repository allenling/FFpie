

import dataclasses

from .abs import VideoFilter


@dataclasses.dataclass
class VStack(VideoFilter):
    fname = "vstack"
    nick_name = "vst"
    inputs_count = 2



def main():
    return


if __name__ == "__main__":
    main()
