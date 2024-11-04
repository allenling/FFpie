

import dataclasses

from .abs import AudioFilter


@dataclasses.dataclass
class ABufferSink(AudioFilter):
    fname = "abuffersink"
    nick_name = "abus"


def main():
    return


if __name__ == "__main__":
    main()
