

import dataclasses
import fractions

from ffpie.utils import AVOptConf


class CodecConf(AVOptConf):
    video = False
    audio = False
    codec_name = None


@dataclasses.dataclass
class VideoCodecConf(CodecConf):
    video = True
    bit_rate: int = 2 * 1024 * 1024  # average bitrates
    # max_bit_rate: int = 5 * 1024 * 1024  # PyAV now does not support writing max_bit_rate yet.
    width: int = None
    height: int = None
    framerate: fractions.Fraction = None
    time_base: fractions.Fraction = None
    pix_fmt: str = "yuv420p"
    # None means do not pass this to FFMPEG, and let FFMPEG itself decide how many B frames will be used when encoding.
    # by default, max_b_frames is -1, which means using B frames.
    # if you do not want to introduce any B frames, just set max_b_frames to be 0.
    max_b_frames: int = None

    @property
    def fps(self):
        return float(self.framerate) if self.framerate else None

    def _clean_framerate(self, params, val):
        if val is None:
            return
        tb = params.get("time_base", None)
        if tb is not None:
            return
        params["time_base"] = 1/val
        return

    @fps.setter
    def fps(self, val):
        self.framerate = fractions.Fraction(val)
        return

    @property
    def tb(self):
        if self.time_base:
            return self.time_base
        if self.framerate:
            return 1/self.framerate
        return


@dataclasses.dataclass
class AudioCodecConf(CodecConf):
    audio = True
    sample_rate: int = 44100
    layout: str = "stereo"
    format: str = "fltp"


class EncoderAbs:
    codec_conf = None

    def encode(self, frame):
        raise NotImplementedError

    @classmethod
    def from_conf(cls, codec_conf: CodecConf):
        return cls(codec_conf)


def main():
    return


if __name__ == "__main__":
    main()
