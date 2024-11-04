

import fractions
from collections import deque

import numpy as np

import av
from av.audio.frame import format_dtypes

from .abs import AudioFrameSampler


def get_ndarray_for_fmt(fmt, layout, nsamples):
    av_fmt = fmt
    if type(fmt) == str:
        av_fmt = av.AudioFormat(fmt)
    dtype = np.dtype(format_dtypes[av_fmt.name])
    if type(layout) == str:
        layout = av.AudioLayout(layout)
    channels = len(layout.channels)
    if av_fmt.is_planar:
        ndarray = np.zeros((channels, nsamples), dtype=dtype)
    else:
        ndarray = np.zeros((1, nsamples * channels), dtype=dtype)
    return ndarray



def copy_audio_frame_ndarray(inarray, outarray, nsamples, instart=0, outstart=0):
    for idx, inchannel_data in enumerate(inarray):
        outchannel_data = outarray[idx]
        outchannel_data[outstart:outstart+nsamples] = inchannel_data[instart:instart+nsamples]
    return



class AudioCommonSampler(AudioFrameSampler):
    audio = True

    def __init__(self, min_samples=None, fmt=None, layout=None, sample_rate=None, codec_ctx=None):
        if codec_ctx:
            # make sure your codec context is open already,
            # otherwise we will be able to get a frame_size of None.
            self.fmt = codec_ctx.format
            self.layout = codec_ctx.layout
            self.sample_rate = codec_ctx.sample_rate
            self.min_samples = codec_ctx.frame_size
        else:
            self.fmt = fmt
            self.layout = layout
            self.sample_rate = sample_rate
            self.min_samples = min_samples
        self.fmt = getattr(self.fmt, "name", self.fmt)
        self.layout = getattr(self.layout, "name", self.layout)
        self.buffer = deque([])
        self.nsamples = 0  # how many samples we've accumulated
        self.resampler = av.AudioResampler(self.fmt, self.layout, self.sample_rate)
        self.pts = 0
        self.tb = fractions.Fraction(1, self.sample_rate)
        return

    def _consume_one(self):
        # TODO: copy-paste function av_samples_copy from ffmpeg for better performance
        nsamples = 0
        nb_frames = 0
        for frame in self.buffer:
            nsamples += frame.samples
            if nsamples > self.min_samples:
                nsamples = self.min_samples
                break
            nb_frames += 1
        new_array = get_ndarray_for_fmt(self.fmt, self.layout, nsamples)
        nsamples = 0
        while nb_frames:
            frame = self.buffer.popleft()
            array = frame.to_ndarray()
            copy_audio_frame_ndarray(array, new_array, nsamples=frame.samples, instart=0, outstart=nsamples)
            nsamples += frame.samples
            nb_frames -= 1
        if (nb_frames == 0 or nsamples < self.min_samples) and self.buffer:
            # we need extract extra data from the first frame to meet self.min_samples
            frame = self.buffer.popleft()
            n = self.min_samples - nsamples
            array = frame.to_ndarray()
            copy_audio_frame_ndarray(array, new_array, nsamples=n, instart=0, outstart=nsamples)
            amount_left = frame.samples - n
            new_first_array = get_ndarray_for_fmt(self.fmt, self.layout, amount_left)
            copy_audio_frame_ndarray(array, new_first_array, nsamples=amount_left, instart=n, outstart=0)
            new_first_frame = av.AudioFrame.from_ndarray(new_first_array, self.fmt, self.layout)
            self.buffer.appendleft(new_first_frame)
            nsamples = self.min_samples
        out = av.AudioFrame.from_ndarray(new_array, format=self.fmt, layout=self.layout)
        out.sample_rate = self.sample_rate
        out.pts = self.pts
        out.time_base = self.tb
        self.pts += nsamples
        self.nsamples -= out.samples
        return out

    def _consume_all(self):
        while self.buffer:
            out = self._consume_one()
            yield out
        return

    def sample(self, frame):
        frames = self.resampler.resample(frame)
        for frame in frames:
            self.nsamples += frame.samples
            self.buffer.append(frame)
        if frame is None:
            yield from self._consume_all()
            return
        while self.nsamples >= self.min_samples:
            out = self._consume_one()
            yield out
        return



def main():
    return


if __name__ == "__main__":
    main()
