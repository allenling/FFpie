


import dataclasses


FILTERS_MAP = {}

NICK_NAMES_MAP = {}

AUDIO_FILTERS = set()


class FilterMeta(type):

    def __new__(cls, class_name, parents, attrs):
        if class_name in ["FilterConfAbs", "VideoFilter", "AudioFilter"]:
            return super().__new__(cls, class_name, parents, attrs)
        global FILTERS_MAP
        fname, nick_name = attrs["fname"], attrs["nick_name"]
        if fname in FILTERS_MAP or nick_name in NICK_NAMES_MAP:
            raise
        FILTERS_MAP[fname] = class_name
        NICK_NAMES_MAP[nick_name] = class_name
        attrs["nick_to_params"] = {}
        p = attrs.get("params_to_nick", {})
        for k, v in p.items():
            attrs["nick_to_params"][v] = k
        return super().__new__(cls, class_name, parents, attrs)


@dataclasses.dataclass
class FilterConfAbs(metaclass=FilterMeta):
    name: str = None  # name specified by the user
    fname = None  # filter's name
    nick_name = None  # for short
    inputs_count = 1
    outputs_count = 1
    video = False
    audio = False
    params_to_nick = {}
    nick_to_params = {}
    DELI = ":"

    def get_avparams(self):
        return dataclasses.asdict(self)

    def to_filter_params(self):
        return {"fname": self.fname, "params": self.get_avparams()}

    def _dict_to_str(self, params, need_name=False):
        ret = []
        for k, v in params.items():
            if k in self.params_to_nick:
                k = self.params_to_nick[k]
            if v is None:
                continue
            if k == "name" and need_name is False:
                continue
            ret.append(f"{k}={v}")
        return f"{self.DELI}".join(ret)

    def to_params_str(self, need_name=True):
        params = self.get_avparams()
        return self._dict_to_str(params, need_name=need_name)

    @classmethod
    def parse_params_str(cls, params_str):
        values = params_str.split(cls.DELI)
        ret = {}
        for val in values:
            k, v = val.split("=")
            if k in cls.nick_to_params:
                k = cls.nick_to_params[k]
            ret[k] = v
        return ret

    @classmethod
    def from_params_str(cls, params_str, **kwargs) -> "FilterConfAbs":
        if not params_str and not kwargs:
            return cls()
        data = {}
        if params_str:
            data = cls.parse_params_str(params_str)
        data.update(**kwargs)
        obj = cls(**data)
        obj._update_params_str()
        return obj

    def _update_params_str(self):
        return


@dataclasses.dataclass
class VideoFilter(FilterConfAbs):
    video = True


@dataclasses.dataclass
class AudioFilter(FilterConfAbs):
    audio = True

    def __new__(cls, *args, **kwargs):
        global AUDIO_FILTERS
        AUDIO_FILTERS.add(cls.fname)
        return super().__new__(cls)


def main():
    return


if __name__ == "__main__":
    main()
