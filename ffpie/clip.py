

import fractions

from typing import List, Type
import dataclasses

from .encoders.abs import VideoCodecConf, AudioCodecConf, EncoderAbs
from .graph import Graph, filters
from .source import OutContainer, Source
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
        self._video_track: VideoTrack | None = None
        self._audio_track: AudioTrack | None = None
        return

    def add_video_track(self, track_conf: VideoTrack):
        self._video_track = dataclasses.replace(track_conf)
        return

    def add_audio_track(self, track_conf: AudioTrack):
        self._audio_track = dataclasses.replace(track_conf)
        return

    def run(self):
        if not self._video_track and not self._audio_track:
            raise
        with OutContainer(self.outpath) as oc:
            self._add_video_stream(oc)
            self._add_audio_stream(oc)
            self._write_video(oc)
            self._write_audio(oc)
            oc.flush_video()
            oc.flush_audio()
        for i in self._video_track.input_sources:
            i.close()
        for i in self._audio_track.input_sources:
            i.close()
        return

    def _choose_video_encoder(self, oc, ):
        if self._video_track.encoder:
            oc.video_encoder = self._video_track.encoder
        elif self._video_track.encoder_cls:
            oc.video_encoder = self._video_track.encoder_cls.from_conf(self._video_track.codec_conf)
        return

    def _add_video_stream(self, oc):
        if not self._video_track:
            return
        input_sources = self._video_track.input_sources
        codec_conf = self._video_track.codec_conf
        fps_mode = self._video_track.fps_mode
        first_source = input_sources[0]
        if not codec_conf.framerate:
            fr = first_source.frame_rate
            # manually specify framerate, or we will take the framerate of the first source
            codec_conf.framerate = fr if fr else self.DEFAULT_FRAME_RATE
        frm = self._video_track.frm
        if not frm:
            if not fps_mode or fps_mode == FPSMode.CFR:
                # manually specify start_time, or we will take the start_time of the first source
                # but in general, you shouldn't have a start time other than 0.
                # why? take a look at how concat demuxing works.
                frm = CFRSampler(codec_conf.framerate, first_source.start_time)
            else:
                raise KeyError(f"{fps_mode} is not supported")
        self._video_track.frm = frm
        oc.add_stream(codec_conf)
        self._choose_video_encoder(oc)
        return

    def _choose_audio_encoder(self, oc):
        if self._audio_track.encoder:
            oc.audio_encoder = self._audio_track.encoder
        elif self._audio_track.encoder_cls:
            oc.audio_encoder = self._audio_track.encoder_cls.from_conf(self._audio_track.codec_conf)
        return

    def _add_audio_stream(self, oc):
        if not self._audio_track:
            return
        oc.add_stream(self._audio_track.codec_conf)
        self._choose_audio_encoder(oc)
        return

    def _write_video(self, oc):
        if not self._video_track:
            return
        frm = self._video_track.frm
        g = self._video_track.g or FakeGraph()
        if not g.n_in_filters:
            inputs = [filters.Buffer(template=i.video_stream) for i in self._video_track.input_sources]
            g.setup_inputs(*inputs)
        gens = [i.read_video_frames() for i in self._video_track.input_sources]
        for frames in zip(*gens):
            # if there's multiple outputs, how are we supposed to know which one to take out.
            # so the graph must have only one output!
            outframe = g.apply_frames(*frames)[0]
            if not outframe:
                continue
            for rframe in frm.sample(outframe):
                oc.mux_one_video_frame(rframe)
        frm.flush_to_oc(oc)
        return

    def _write_audio(self, oc):
        if not self._audio_track:
            return
        frm = self._audio_track.frm
        if frm is None:
            oc.acodec_ctx.open(strict=False)
            frm = AudioCommonSampler(codec_ctx=oc.acodec_ctx)
        g = self._audio_track.g or FakeGraph()
        if not g.n_in_filters:
            inputs = [filters.ABuffer(template=i.audio_stream) for i in self._audio_track.input_sources]
            g.setup_inputs(*inputs)
        gens = [i.read_audio_frames() for i in self._audio_track.input_sources]
        for frames in zip(*gens):
            outframe = g.apply_frames(*frames)[0]
            if not outframe:
                continue
            for rframe in frm.sample(outframe):
                oc.mux_one_audio_frame(rframe)
        frm.flush_to_oc(oc)
        return



def main():
    return


if __name__ == "__main__":
    main()
