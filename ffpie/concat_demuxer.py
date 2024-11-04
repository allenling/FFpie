

from typing import List

from .source import Source, OutContainer
from .utils import random_strings
from .ffutils import av_rescale_q_near_inf
from .constants import AV_TIME_BASE_Q


class SimpleConcat:

    """
    from ffmpeg concat demuxer:
    All files must have the same streams (same codecs, same time base, etc.) but can be wrapped in different container formats.

    here we assume that every input file starts at 0 second.
    because, say we are having one key frame every second in each file, and we are concating two files, but we want to skip the
    frames of the first 2.5s in the second file.
    basically concat the second file starting at 2.5 seconds to the end of the first file, then the merged file can not be displayed
    correctly, because the frames from 2.5s to 3s are not going to be decoded correctly as losing the key frame at 2s.

    to fix this, you have to decode the packets from 2s to 3s of the second video file, then encode them using the same configuration,
    get the packets, then append those packets to the end of the first file before the rest of the packets of the
    second file starting at 3s.
    """

    def __init__(self, outpath: str | None = None,
                 paths: List[str] | None = None,
                 sources: List[Source] | None = None,
                 ):
        if not paths and not sources:
            raise
        self.sources = sources
        if sources is None:
            self.sources = [Source(p) for p in paths]
        #
        self.outpath = outpath or f"{random_strings(8)}.mp4"
        return

    def demux(self):
        with OutContainer(self.outpath) as oc:
            video_stream = audio_stream = None
            # find the first video stream and audio stream
            for s in self.sources:
                if not video_stream:
                    video_stream = s.video_stream
                if not audio_stream:
                    audio_stream = s.audio_stream
                if video_stream and audio_stream:
                    break
            if video_stream:
                oc.add_stream(template=video_stream)
            if audio_stream:
                oc.add_stream(template=audio_stream)
            start_time = 0
            for s in self.sources:
                start_time = self.demux_source(oc, s, start_time)
        return

    def demux_source(self, oc, s, start_time=0):
        if s.video_stream:
            start_video_pts = av_rescale_q_near_inf(start_time, AV_TIME_BASE_Q, s.video_time_base)
            for packet in s.read_video_packets():
                packet.dts += start_video_pts
                packet.pts += start_video_pts
                oc.mux_one_video(packet)
        #
        if s.audio_stream:
            s.seek(0)
            start_audio_pts = av_rescale_q_near_inf(start_time, AV_TIME_BASE_Q, s.audio_time_base)
            for packet in s.read_audio_packets():
                packet.dts += start_audio_pts
                packet.pts += start_audio_pts
                oc.mux_one_audio(packet)
        return start_time + s.duration




def main():
    return


if __name__ == "__main__":
    main()
