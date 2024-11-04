


import dataclasses

from .abs import VideoFilter


@dataclasses.dataclass
class Concat(VideoFilter):
    fname = "concat"
    nick_name = "cat"
    n: int = 2
    v: int = 1
    a: int = 1

    def get_avparams(self):
        return {"n": f"{self.n}", "v": f"{self.v}", "a": f"{self.a}"}


def main():
    return


if __name__ == "__main__":
    main()
