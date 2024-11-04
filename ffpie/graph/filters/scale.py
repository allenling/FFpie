



import dataclasses

from .abs import VideoFilter


@dataclasses.dataclass
class Scale(VideoFilter):
    fname = "scale"
    nick_name = "sc"
    params_to_nick = {"width": "w", "height": "h"}
    #
    width: str = "iw"
    height: str = "ih"



def main():
    return


if __name__ == "__main__":
    main()
