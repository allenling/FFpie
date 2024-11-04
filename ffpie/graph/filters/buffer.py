

import dataclasses
from fractions import Fraction

from av.video.stream import VideoStream

from .abs import VideoFilter


@dataclasses.dataclass
class Buffer(VideoFilter):
    fname = "buffer"
    nick_name = "bu"
    template: VideoStream = None
    width: int = None
    height: int = None
    format: str = None
    time_base: Fraction = None

    def get_avparams(self):
        if self.template is not None:
            return {"template": self.template, "name": self.name}
        t = self.template
        del self.template
        data = dataclasses.asdict(self)
        self.template = t
        return data

    def to_params_str(self, need_name=False):
        w, h, f, t = self.width, self.height, self.format, str(self.time_base)
        if self.template is not None:
            w = self.template.width
            h = self.template.height
            f = self.template.format.name
            t = str(self.template.time_base)
        params = {"width": w, "height": h, "format": f, "time_base": t}
        return self._dict_to_str(params, need_name=need_name)

    def _update_params_str(self):
        self.time_base = Fraction(self.time_base)
        return


def main():
    return


if __name__ == "__main__":
    main()
