


import os
import logging
import fractions

import av
from av.video.stream import VideoStream

from .constants import AV_TIME_BASE
from .utils import StoppableClass
from .decoders.h264_cuvid import H264Cuvid
from .encoders.abs import CodecConf


logger = logging.getLogger(__file__)



class SeekConf:

    def __init__(self, start=None, end=None, exclusive_end=False, leftmost=False, rightmost=False):
        self.start = start
        self.end = end
        self.exclusive_end = exclusive_end
        self.leftmost = leftmost  # the leftmost key frame included
        self.rightmost = rightmost  # the rightmost key frame included
        self._end_frame = False
        if start is None:
            self.start = 0
        if self.end and self.start > self.end:
            raise KeyError("start can not be greater than end")
        if exclusive_end and (self.leftmost or self.rightmost):
            raise KeyError("canot set both exclusive_end and rightmost to be True")
        return

    def check_in_range(self, key_frame, pts_time):
        # the first frame decoded must be a keyframe, and must be the leftmost frame.
        if pts_time < self.start:
            if self.leftmost:
                return True
            return False
        if self.end and pts_time >= self.end:
            if self.exclusive_end:
                return
            if self.rightmost:
                if key_frame:
                    self._end_frame = True
                    return True
                if self._end_frame:
                    return
            elif pts_time > self.end:
                return
        return True


class Source(StoppableClass):

    def __init__(self, path, video_idx=0, audio_idx=0):
        self.path = path
        self.name = os.path.split(path)[-1]
        self.container = av.open(path)
        self.video_stream = None
        self.audio_stream = None
        self.video_duration = 0
        self.audio_duration = 0
        self.duration = self.container.duration
        if self.container.streams.video:
            self.video_stream = self.container.streams.video[video_idx]
            self.width, self.height = self.video_stream.width, self.video_stream.height
            self.frame_rate = self.video_stream.average_rate
            self.format = self.video_stream.format
            self.fps = round(self.frame_rate)
            self.video_time_base = self.video_stream.time_base
            if self.video_stream.duration:
                self.video_duration = float(self.video_stream.duration * self.video_stream.time_base)
            self.video_frames = self.video_stream.frames
            self.set_video_thread_nums(os.cpu_count())
        #
        if self.container.streams.audio:
            self.audio_stream = self.container.streams.audio[audio_idx]
            self.audio_sample_rate = self.audio_stream.sample_rate
            self.audio_channels = self.audio_stream.channels
            self.audio_format = self.audio_stream.format
            self.audio_layout = self.audio_stream.layout
            self.audio_time_base = self.audio_stream.time_base
            self.audio_duration = float(self.audio_stream.duration * self.audio_stream.time_base)
        #
        self.seek_conf = SeekConf()
        return

    def __str__(self):
        return f"ContainerSource<{self.path}>"

    def __repr__(self):
        return self.__str__()

    def set_video_thread_nums(self, n):
        self.video_stream.thread_type = "AUTO"
        self.video_stream.thread_count = n
        return

    def seek(self, start, end=None, exclusive_end=False, leftmost=False, rightmost=False):
        self.seek_conf = SeekConf(start=start, end=end, exclusive_end=exclusive_end,
                                  leftmost=leftmost, rightmost=rightmost)
        self.container.seek(int(start * AV_TIME_BASE))
        return

    @property
    def start_time(self):
        return self.seek_conf.start

    def close(self):
        self.container.close()
        self.stop()
        return

    def _reset_decoder(self):
        return

    def _decode(self, packet):
        return packet.decode()

    def _demux_packets(self, demux_obj):
        for packet in demux_obj:
            if packet.pts is None:
                yield packet
                break
            if self.is_stopped:
                break
            yield packet
        return

    def _read_packets(self, demux_obj):
        for packet in self._demux_packets(demux_obj):
            if packet.pts is None:
                continue
            pts_time = float(packet.pts*packet.time_base)
            # due to b frames, it's not guaranteed that all packets in the range will be returned,
            # there's might be some packets left in place untouched.
            res = self.seek_conf.check_in_range(packet.is_keyframe, float(packet.pts*packet.time_base))
            if res is False:
                continue
            if res is None:
                break
            yield packet
        return

    def _read_frames(self, demux_obj):
        for packet in self._demux_packets(demux_obj):
            for frame in self._decode(packet):
                key_frame = getattr(frame, "key_frame", True)
                res = self.seek_conf.check_in_range(key_frame, frame.time)
                if res is False:
                    continue
                if res is None:
                    return
                yield frame
        return

    def read_video_frames(self):
        if self.is_stopped:
            return
        demux_obj = self.container.demux(self.video_stream)
        self._reset_decoder()
        yield from self._read_frames(demux_obj)
        return

    def read_audio_frames(self):
        if self.is_stopped:
            return
        demux_obj = self.container.demux(self.audio_stream)
        self._reset_decoder()
        yield from self._read_frames(demux_obj)
        return

    def read_video_packets(self):
        if self.is_stopped:
            return
        demux_obj = self.container.demux(self.video_stream)
        yield from self._read_packets(demux_obj)
        return

    def read_audio_packets(self):
        if self.is_stopped:
            return
        demux_obj = self.container.demux(self.audio_stream)
        yield from self._read_packets(demux_obj)
        return


class HWSourceAbs(Source):

    def _reset_decoder(self):
        raise NotImplementedError

    def _decode(self, packet):
        raise NotImplementedError



class H264HWSource(HWSourceAbs):

    def _reset_decoder(self):
        self.decoder = H264Cuvid(stream=self.video_stream)
        return

    def _decode(self, packet):
        return self.decoder.decode(packet=packet)


class ImageReader(StoppableClass):

    def __init__(self, path, duration=None, fps=None):
        self.path = path
        self.duration = duration
        self.container = av.open(path)
        self.frame = next(self.container.decode(video=0))
        self.stream = self.container.streams.video[0]
        self.frame.time_base = fractions.Fraction(1, fps) if fps else self.container.streams.video[0].time_base
        self.frame.pts = 0
        return

    def read_video_frames(self):
        while not self.is_stopped:
            if self.duration and self.frame.time >= self.duration:
                break
            yield self.frame
            self.frame.pts += 1
        return

    def close(self):
        self.container.close()
        return


class OutContainer:

    def __init__(self, path, codec_conf=None, template=None,
                 video_encoder=None,
                 audio_encoder=None):
        local_dir = os.path.dirname(path)
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)
        self.path = path
        self.container = av.open(path, "w")
        self.video_stream = self.audio_stream = None
        self.fps = None
        self.time_base = None
        self.video_encoder = video_encoder
        self.audio_encoder = audio_encoder
        if codec_conf or template:
            self.add_stream(codec_conf, template)
        self._video_flushed = False
        self._audio_flushed = False
        return

    def __str__(self):
        return f"OC<{self.path}>"

    def __repr__(self):
        return self.__str__()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return

    def add_stream(self, codec_conf: CodecConf = None, template=None):
        if codec_conf:
            codec_name = codec_conf.codec_name
            conf_params = codec_conf.get_conf_params()
            rate = conf_params.get("framerate", None) or conf_params.get("sample_rate", None)
            stream = self.container.add_stream(codec_name, rate=rate, **conf_params)
        else:
            stream = self.container.add_stream(template=template)
        if isinstance(stream, VideoStream):
            self.video_stream = stream
            self.video_encoder = self.video_encoder or stream
        else:
            self.audio_stream = stream
            self.audio_encoder = self.audio_encoder or stream
        return

    def mux_one_video(self, packet):
        if not self.video_stream:
            raise KeyError("add a video stream before muxing any video packets")
        packet.stream = self.video_stream
        self.container.mux_one(packet)
        return

    def mux_one_video_frame(self, frame):
        for packet in self.video_encoder.encode(frame):
            self.mux_one_video(packet)
        return

    def mux_one_audio(self, packet):
        if not self.audio_stream:
            raise KeyError("add a audio stream before muxing any audio packets")
        packet.stream = self.audio_stream
        self.container.mux_one(packet)
        return

    def mux_one_audio_frame(self, frame):
        for packet in self.audio_encoder.encode(frame):
            self.mux_one_audio(packet)
        return

    def flush_video(self):
        if self._video_flushed:
            return
        for packet in self.video_encoder.encode(None):
            self.mux_one_video(packet)
        self._video_flushed = True
        return

    def flush_audio(self):
        if self._audio_flushed:
            return
        for packet in self.audio_encoder.encode(None):
            self.mux_one_audio(packet)
        self._audio_flushed = True
        return

    def close(self):
        self.container.close()
        return

    @property
    def vcodec_ctx(self):
        return self.video_encoder.codec_context

    @property
    def acodec_ctx(self):
        return self.audio_encoder.codec_context


def main():
    return


if __name__ == "__main__":
    main()
