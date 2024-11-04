

from enum import Enum

from fractions import Fraction

import av

AV_TIME_BASE = 1000 * 1000

AV_TIME_BASE_Q = Fraction(1, AV_TIME_BASE)

CPU_H264_ENCODER = "libx264"
CPU_H264_DECODER = "h264"
CUDA_H264_CODEC = "h264_nvenc"
CUDA_H264_HWACCE = "h264_cuvid"

IFrame = av.video.frame.PictureType.I
NONEFrame = av.video.frame.PictureType.NONE


class FPSMode(Enum):
    AUTO = -1
    PASSTHROUGH = 0
    CFR = 1
    VFR = 2


def main():
    return


if __name__ == "__main__":
    main()
