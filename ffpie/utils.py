

import random
import string

import av


from .constants import CUDA_H264_CODEC, CUDA_H264_HWACCE


RANDOM_SET = string.digits + string.ascii_letters


class AVOptConf:
    _force_str = False
    _force_any = True
    _exclusive_keys = []

    def get_conf_params(self) -> dict:
        opts = {}
        keys = self.__dataclass_fields__.keys()
        vals = [getattr(self, key) for key in keys if not key.startswith("_")]
        if not any(vals):
            if self._force_any:
                raise KeyError("at least one attribute is not None")
            return {}
        for key, val in zip(keys, vals):
            if key in self._exclusive_keys:
                continue
            if val is None:
                continue
            if isinstance(val, AVOptConf):
                val = val.get_conf_params()
            else:
                if self.__dataclass_fields__[key].type == bool:
                    val = 1 if val else 0
                if self._force_str:
                    val = f"{val}"
            opts[key] = val
        for key in list(opts.keys()):
            opt_func = getattr(self, f"_clean_{key}", None)
            if opt_func is None:
                continue
            opt_func(opts, opts[key])
        return opts


class StoppableClass:

    _stop = False

    @property
    def is_stopped(self):
        return self._stop

    def stop(self):
        self._stop = True
        return


def has_cuda_h264_encodec():
    return CUDA_H264_CODEC in av.codecs_available


def has_cuda_h264_hwaccel():
    return CUDA_H264_HWACCE in av.codecs_available


def is_annexb(packet: av.Packet | bytes | None) -> bool:
    if packet is None:
        return False
    data = memoryview(packet)
    head = list(data[:4])
    return head == [0, 0, 0, 1] or head[:3] == [0, 0, 1]


def random_strings(size=6):
    return ''.join(random.choice(RANDOM_SET) for _ in range(size))


def main():
    return


if __name__ == "__main__":
    main()
