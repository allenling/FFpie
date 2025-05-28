


from .h264 import H264Conf, H264Opts, NVENCConf, NVENCOpts, H264Encoder
from .aac import AACConf, AACEncoder


CODECS_MAP = {H264Conf.codec_name: H264Encoder,
              NVENCConf.codec_name: H264Encoder,
              AACConf.codec_name: AACEncoder,
              }


def get_encoder(codec_conf):
    cls = CODECS_MAP.get(codec_conf.codec_name, None)
    return cls(codec_conf)


def main():
    return


if __name__ == "__main__":
    main()
