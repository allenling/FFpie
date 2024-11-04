


import dataclasses

from av.audio.stream import AudioStream

from .abs import AudioFilter


@dataclasses.dataclass
class ABuffer(AudioFilter):
    fname = "abuffer"
    nick_name = "abu"
    template: AudioStream = None
    sample_rate: int = None
    format: str = None
    layout: str = None
    channels: int = 2

    def get_avparams(self):
        if self.template is not None:
            return {"template": self.template, "name": self.name}
        t = self.template
        del self.template
        data = dataclasses.asdict(self)
        self.template = t
        return data

    def to_params_str(self, need_name=False):
        s, f, l, c = self.sample_rate, self.format, self.layout, self.channels
        if self.template is not None:
            s = self.template.sample_rate
            f = self.template.format
            l = self.template.layout
            c = self.template.channels
        params = {"sample_rate": s, "format": f, "layout": l, "channels": c}
        return self._dict_to_str(params, need_name=need_name)


def main():
    return


if __name__ == "__main__":
    main()
