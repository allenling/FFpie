


import dataclasses

import av

from .abs import AudioCodecConf, EncoderAbs


@dataclasses.dataclass
class AACConf(AudioCodecConf):
    _force_str = False
    codec_name = "aac"
    supported_samples_rates = [96000, 88200, 64000, 48000, 44100, 32000, 24000, 22050, 16000, 12000, 11025, 8000, 7350]
    supported_format = "fltp"
    #

    def _clean_sample_rate(self, params, val):
        if val not in self.supported_samples_rates:
            raise
        return

    def _clean_formt(self, params, val):
        if val != self.supported_format:
            raise
        return


class AACEncoder(EncoderAbs):

    def __init__(self, codec_conf: AACConf):
        self.codec_conf = codec_conf
        self.codec = av.Codec(codec_conf.codec_name, "w")
        self.codec_conf = codec_conf
        self.codec_ctx = av.CodecContext.create(self.codec)
        self.codec_ctx.sample_rate = self.sample_rate = codec_conf.sample_rate
        self.codec_ctx.layout = self.layout = codec_conf.layout
        self.codec_ctx.format = self.format = codec_conf.format
        self.codec_ctx.open()
        return

    def encode(self, frame):
        return self.codec_ctx.encode(frame)


def main():
    return


if __name__ == "__main__":
    main()
