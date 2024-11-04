


import dataclasses
from fractions import Fraction

from .abs import VideoFilter


@dataclasses.dataclass
class Setpts(VideoFilter):
    fname = "setpts"
    nick_name = "sp"
    #
    speed: float = 1

    def validate(self):
        return self.speed == 1

    def get_avparams(self):
        return {"expr": f"{float(1/Fraction(self.speed))}*PTS"}


def main():
    return


if __name__ == "__main__":
    main()
