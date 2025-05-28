

import fractions
import tempfile
from typing import List, Type
import dataclasses

from .encoders.abs import VideoCodecConf, AudioCodecConf, EncoderAbs
from .graph import Graph, filters
from .source import OutContainer, Source, PacketOutContainer
from .frames_samplers.abs import VideoFrameSampler, AudioFrameSampler
from .frames_samplers import CFRSampler, AudioCommonSampler
from .utils import random_strings
from .constants import FPSMode


class FakeGraph(Graph):
    configured = True
    n_in_filters = 1
    n_out_filters = 1

    def apply_frames(self, *frames):
        return frames


@dataclasses.dataclass
class VideoTrack:
    input_sources: List[Source]
    codec_conf: VideoCodecConf
    fps_mode: FPSMode | None = None
    encoder_cls: Type[EncoderAbs] | None = None
    encoder: EncoderAbs | None = None
    g: Graph | None = None
    frm: VideoFrameSampler | None = None


@dataclasses.dataclass
class AudioTrack:
    input_sources: List[Source]
    codec_conf: AudioCodecConf
    encoder_cls: Type[EncoderAbs] | None = None
    encoder: EncoderAbs | None = None
    g: Graph | None = None
    frm: AudioFrameSampler | None = None


class Clip:
    DEFAULT_FRAME_RATE = fractions.Fraction(25, 1)

    def __init__(self, outpath: str = None):
        self.outpath = outpath or f"{random_strings(8)}.mp4"
        self.video_track: VideoTrack | None = None
        self.audio_track: AudioTrack | None = None
        return

    def add_video_track(self, track_conf: VideoTrack):
        self.video_track = dataclasses.replace(track_conf)
        return

    def add_audio_track(self, track_conf: AudioTrack):
        self.audio_track = dataclasses.replace(track_conf)
        return

    def _init_video_stream(self, oc):
        oc.add_stream(self.video_track.codec_conf)
        if self.video_track.encoder:
            oc.video_encoder = self.video_track.encoder
        elif self.video_track.encoder_cls:
            oc.video_encoder = self.video_track.encoder_cls.from_conf(self.video_track.codec_conf)
        return

    def _init_video_track(self):
        input_sources = self.video_track.input_sources
        codec_conf = self.video_track.codec_conf
        fps_mode = self.video_track.fps_mode
        first_source = input_sources[0]
        if not codec_conf.framerate:
            fr = first_source.frame_rate
            # manually specify framerate, or we will take the framerate of the first source
            codec_conf.framerate = fr if fr else self.DEFAULT_FRAME_RATE
        if not self.video_track.frm:
            if not fps_mode or fps_mode == FPSMode.CFR:
                # manually specify start_time, or we will take the start_time of the first source
                # but in general, you shouldn't have a start time other than 0.
                # why? take a look at how concat demuxing works.
                frm = CFRSampler(codec_conf.framerate, first_source.start_time)
                self.video_track.frm = frm
            else:
                raise KeyError(f"{fps_mode} is not supported yet")
        return

    def _add_video_stream(self, oc):
        if not self.video_track:
            return
        self._init_video_track()
        if self.video_track.codec_conf.width and self.video_track.codec_conf.height:
            self._init_video_stream(oc)
        return

    def _read_video_frames(self):
        gens = [i.read_video_frames() for i in self.video_track.input_sources]
        for frames in zip(*gens):
            yield frames
        return

    def _init_video_graph(self):
        g = self.video_track.g or FakeGraph()
        if not g.n_in_filters:
            inputs = [filters.Buffer(template=i.video_stream) for i in self.video_track.input_sources]
            g.set_inputs(*inputs)
        return g

    def filtered_video_frames(self, oc):
        frm = self.video_track.frm
        g = self._init_video_graph()
        for frames in self._read_video_frames():
            # if there's multiple outputs, how are we supposed to know which one to take out.
            # so the graph must have only one output!
            outframe = g.apply_frames(*frames)[0]
            if not outframe:
                continue
            if not self.video_track.codec_conf.width or not self.video_track.codec_conf.height:
                self.video_track.codec_conf.width = outframe.width
                self.video_track.codec_conf.height = outframe.height
                self._init_video_stream(oc)
            for rframe in frm.sample(outframe):
                yield rframe
        for rframe in frm.flush():
            yield rframe
        return

    def _write_video(self, oc):
        if not self.video_track:
            return
        for rframe in self.filtered_video_frames(oc):
            oc.mux_one_video_frame(rframe)
        return

    def _init_audio_track(self):
        return

    def _add_audio_stream(self, oc):
        if not self.audio_track:
            return
        self._init_audio_track()
        oc.add_stream(self.audio_track.codec_conf)
        if self.audio_track.encoder:
            oc.audio_encoder = self.audio_track.encoder
        elif self.audio_track.encoder_cls:
            oc.audio_encoder = self.audio_track.encoder_cls.from_conf(self.audio_track.codec_conf)
        return

    def _init_audio_graph(self):
        g = self.audio_track.g or FakeGraph()
        if not g.n_in_filters:
            inputs = [filters.ABuffer(template=i.audio_stream) for i in self.audio_track.input_sources]
            g.set_inputs(*inputs)
        return g

    def _read_audio_frames(self):
        gens = [i.read_audio_frames() for i in self.audio_track.input_sources]
        for frames in zip(*gens):
            yield frames
        return

    def filtered_audio_frames(self, oc):
        frm = self.audio_track.frm
        if frm is None:
            oc.acodec_ctx.open(strict=False)
            frm = AudioCommonSampler(codec_ctx=oc.acodec_ctx)
        g = self._init_audio_graph()
        for frames in self._read_audio_frames():
            outframe = g.apply_frames(*frames)[0]
            if not outframe:
                continue
            for rframe in frm.sample(outframe):
                yield rframe
        for rframe in frm.flush():
            yield rframe
        return

    def _write_audio(self, oc):
        if not self.audio_track:
            return
        for rframe in self.filtered_audio_frames(oc):
            oc.mux_one_audio_frame(rframe)
        return

    def close_video_sources(self):
        if not self.video_track:
            return
        for i in self.video_track.input_sources:
            i.close()
        return

    def close_audio_sources(self):
        if not self.audio_track:
            return
        for i in self.audio_track.input_sources:
            i.close()
        return

    def run(self):
        assert self.video_track or self.audio_track
        with OutContainer(self.outpath) as oc:
            self._add_video_stream(oc)
            self._add_audio_stream(oc)
            self._write_video(oc)
            self._write_audio(oc)
            if self.video_track:
                oc.flush_video()
            if self.audio_track:
                oc.flush_audio()
        self.close_video_sources()
        self.close_audio_sources()
        return

    def gen_video_packets(self):
        if not self.video_track:
            return
        assert self.video_track.encoder_cls or self.video_track.encoder
        with PacketOutContainer() as oc:
            self._add_video_stream(oc)
            for rframe in self.filtered_video_frames(oc):
                yield from oc.mux_one_video_frame(rframe)
            yield from oc.flush_video()
        self.close_video_sources()
        return

    def gen_audio_packets(self):
        if not self.audio_track:
            return
        assert self.audio_track.encoder_cls or self.audio_track.encoder
        with PacketOutContainer() as oc:
            self._add_audio_stream(oc)
            for rframe in self.filtered_audio_frames(oc):
                yield from oc.mux_one_audio_frame(rframe)
        self.close_audio_sources()
        return



def main():
    return


if __name__ == "__main__":
    main()
