

import logging
import dataclasses

import av

from ffpie.constants import CPU_H264_ENCODER, CUDA_H264_CODEC

from .abs import AVOptConf, VideoCodecConf, EncoderAbs
from .utils import ForcedIDR

logger = logging.getLogger(__file__)



@dataclasses.dataclass
class H264Opts(AVOptConf):
    _force_str = True
    #
    forced_idr: bool = True
    preset: str = "medium"  #
    profile: str = "main"  #

    def _clean_forced_idr(self, params, val):
        params["forced-idr"] = val
        del params["forced_idr"]
        return


@dataclasses.dataclass
class H264Conf(VideoCodecConf):
    _force_str = False
    #
    codec_name = CPU_H264_ENCODER
    options: H264Opts = None

    def _get_bit_rate(self, params, val):
        if self.options and self.options.cq is not None and self.bit_rate is not None:
            logger.warning("bitrate would work as expected if you set both bitrate and cq.")
        return

    def set_opt_val(self, key, val):
        if not self.options:
            self.options = self.__dataclass_fields__["options"].type()
        setattr(self.options, key, val)
        return

    @classmethod
    def get_default(cls, options=True, **kwargs):
        if options:
            opts = cls.__dataclass_fields__["options"].type()
            kwargs["options"] = opts
        return cls(**kwargs)


@dataclasses.dataclass
class NVENCOpts(H264Opts):
    cq: int = None  # 25 - 32
    preset: str = "p4"  # slow but good quality
    profile: str = "main"  #
    rc: str = "vbr"
    gpu: int = 0


@dataclasses.dataclass
class NVENCConf(H264Conf):
    codec_name = CUDA_H264_CODEC
    options: NVENCOpts = None


class H264Encoder(EncoderAbs):

    def __init__(self, codec_conf: H264Conf):
        self.codec_conf = codec_conf
        self.frame_count = 0
        self._forced_idr = None
        self.reset_pts = False  # it decides whether to set both frame.pts and frame.time_base to be None
        self.codec = None
        self.codec_ctx = None
        self.params = None
        if codec_conf.width and codec_conf.height:
            self.init_codec_ctx()
        return

    def init_codec_ctx(self, frame=None):
        if self.codec_conf.options and self.codec_conf.options.forced_idr:
            self._forced_idr = ForcedIDR(nseconds=1)
        if frame:
            self.codec_conf.width = frame.width
            self.codec_conf.height = frame.height
        self.codec = av.Codec(self.codec_conf.codec_name, "w")
        self.codec_ctx = av.CodecContext.create(self.codec)
        self.params = self.codec_conf.get_conf_params()
        for k, v in self.params.items():
            setattr(self.codec_ctx, k, v)
        self.codec_ctx.open()
        return

    def __str__(self):
        return f"H264<{self.codec_conf.codec_name}>"

    def __repr__(self):
        return self.__str__()

    def enable_reset_pts(self):
        self.reset_pts = True
        return

    def disable_reset_pts(self):
        self.reset_pts = False
        return

    def forced_idr_seconds(self, n):
        self._forced_idr = ForcedIDR(nseconds=n)
        return

    def forced_idr_frames(self, n):
        self._forced_idr = ForcedIDR(nframes=n)
        return

    def encode(self, frame):
        if not self.codec_ctx:
            self.init_codec_ctx(frame)
        if frame is None:
            return self.codec_ctx.encode(None)
        self.frame_count += 1
        if self._forced_idr:
            self._forced_idr.force(frame)
        if self.reset_pts:
            frame.pts = None
            frame.time_base = None
        return self.codec_ctx.encode(frame)


def main():
    return


if __name__ == "__main__":
    main()
