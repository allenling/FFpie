

import dataclasses

from .abs import AudioFilter


@dataclasses.dataclass
class Atempo(AudioFilter):
    fname = "atempo"
    nick_name = "at"
    audio = True
    speed: float = 1

    def validate(self):
        return self.speed == 1

    def get_avparams(self):
        return {"tempo": f"{self.speed}"}


def main():
    return


if __name__ == "__main__":
    main()
