

import logging


from ffpie.constants import IFrame, NONEFrame

logger = logging.getLogger(__file__)


class ForcedIDR:

    def __init__(self, nseconds: float = None, nframes: int = None):
        self._force_next_key = True
        self.head_ts = 0
        self.frames = 0
        self._next_key_time = 0
        self._next_key_nframe = 0
        self.nseconds = nseconds
        self.nframes = nframes
        return

    def force_next_key(self):
        self._force_next_key = True
        return

    def force(self, frame):
        pict_type = NONEFrame
        if self._force_next_key:
            pict_type = IFrame
            self._force_next_key = False
        elif self.nseconds and frame.time - self.head_ts >= self.nseconds:
            pict_type = IFrame
            self.head_ts = frame.time
        elif self.nframes:
            self.frames += 1
            if self.frames == self.nframes:
                pict_type = IFrame
                self.frames = 0
        if pict_type == IFrame:
            logger.debug(f"I Frame at {frame.time}!")
        frame.pict_type = pict_type
        return




def main():
    return


if __name__ == "__main__":
    main()
