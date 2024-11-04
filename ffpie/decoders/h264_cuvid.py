

import av

from ffpie.utils import CUDA_H264_HWACCE, has_cuda_h264_hwaccel
from .abs import DecoderAbs


class H264Cuvid(DecoderAbs):

    def __init__(self, stream=None, extradata=None):
        if not has_cuda_h264_hwaccel():
            raise
        self.ctx = av.Codec(CUDA_H264_HWACCE, 'r').create()
        self.ctx.extradata = extradata
        if stream:
            self.ctx.extradata = stream.codec_context.extradata
        self._tb = None
        self.output_fmt = "yuv420p"
        return

    def disable_reformat(self):
        self.output_fmt = None
        return

    def set_resize(self, w, h):
        self.ctx.options["resize"] = f"{w}x{h}"
        return

    def set_crop(self, top, left, bottom, right):
        self.ctx.options["crop"] = f"{top}x{bottom}x{left}x{right}"
        return

    def set_gpu(self, gpu=0):
        self.ctx.options["gpu"] = f"{gpu}"
        return

    def decode(self, packet: av.Packet = None, pkt_bytes: bytes = None, dts=None, pts=None):
        if pkt_bytes is not None and packet is not None:
            raise KeyError
        # if not self.ctx.extradata and not utils.is_annexb(pkg_bytes or packet):
        #     raise ValueError("must be Annex B format of data")
        if packet is None and pkt_bytes:
            packet = av.Packet(len(pkt_bytes))
            packet.update(pkt_bytes)
            if dts:
                packet.dts = dts
            if pts:
                packet.pts = pts
        frames = self.ctx.decode(packet)
        if self.output_fmt:
            frames = [frame.reformat(format=self.output_fmt) for frame in frames]
        if not self._tb and frames:
            self._tb = frames[0].time_base
        if frames and frames[0].time_base is None:
            for frame in frames:
                frame.time_base = self._tb
        return frames


def main():
    return


if __name__ == "__main__":
    main()
