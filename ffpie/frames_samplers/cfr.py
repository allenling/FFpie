
import logging

from fractions import Fraction

from ffpie.ffutils import adjust_frame_pts_to_encoder_tb, llrintf
from ffpie.constants import FPSMode

from .abs import VideoFrameSampler


logger = logging.getLogger(__file__)


class CFRSampler(VideoFrameSampler):
    """
    FFmpeg-n6.1.1
    """
    fps_mode = FPSMode.CFR

    DELTA_THRESHOLD_LEFT = -1.1
    DELTA_THRESHOLD_RIGHT = 1.1
    frame_drop_threshold = 0

    def __init__(self,
                 out_fps: float | Fraction,
                 # NOTE: this is not the start at your seek conf!
                 ost_start_time: float = 0,
                 ):
        #
        self.n_drops = 0
        self.n_dups = 0
        self.nframes = 0
        self.tb_out = 1/Fraction(out_fps)
        self.ost_start_time = ost_start_time
        self._last_frame = None
        return

    def sample(self, frame):
        if frame is None:
            return
        nb0_frame = 0
        nb_frame = 1
        duration = frame.duration * float(frame.time_base)/float(self.tb_out)
        sync_ipts = adjust_frame_pts_to_encoder_tb(frame, self.tb_out, self.ost_start_time)
        delta0 = sync_ipts - self.nframes
        delta = delta0 + duration
        if self.frame_drop_threshold and delta < self.frame_drop_threshold and self.nframes:
            nb_frame = 0
        elif delta < self.DELTA_THRESHOLD_LEFT:
            nb_frame = 0
        elif delta > self.DELTA_THRESHOLD_RIGHT:
            nb_frame = llrintf(delta)
            if delta0 > 1.1:
                nb0_frame = llrintf(delta0-0.6)
        # frame.duration = 1
        if nb_frame == 0:
            self._last_frame = frame
            self.n_drops += 1
            return
        if nb_frame > 1:
            self.n_dups += nb_frame - 1
        for i in range(nb_frame):
            frame_in = frame
            if i < nb0_frame:
                frame_in = self._last_frame
            frame_in.pts = self.nframes
            self.nframes += 1
            yield frame_in
        self._last_frame = frame
        return



def main():
    return


if __name__ == "__main__":
    main()
