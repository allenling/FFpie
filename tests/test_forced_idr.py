



from ffpie.encoders.utils import ForcedIDR
from ffpie.constants import IFrame, NONEFrame

from tests.common import yield_frames


class TestSeconds:

    def test_one_second(self):
        fdr = ForcedIDR(nseconds=1)
        for f in yield_frames(61):
            fdr.force(f)
            t = f.time
            if t == int(t):
                assert f.pict_type == IFrame
            else:
                assert f.pict_type == NONEFrame
        return

    def test_two_seconds(self):
        fdr = ForcedIDR(nseconds=2)
        for f in yield_frames(61):
            fdr.force(f)
            t = f.time
            if t == 0 or t == 2:
                assert f.pict_type == IFrame
            else:
                assert f.pict_type == NONEFrame
        return

    def test_onefive_seconds(self):
        fdr = ForcedIDR(nseconds=1.5)
        for f in yield_frames(91):
            fdr.force(f)
            t = f.time
            if t in [0, 1.5, 3]:
                assert f.pict_type == IFrame, f"pts: {f.pts}, t: {t}"
            else:
                assert f.pict_type == NONEFrame, f"pts: {f.pts}, t: {t}"
        return

    def test_seconds(self):
        fdr = ForcedIDR(nseconds=2.2)
        for f in yield_frames(91):
            fdr.force(f)
            t = f.time
            if t in [0, 2.2]:
                assert f.pict_type == IFrame, f"pts: {f.pts}, t: {t}"
            else:
                assert f.pict_type == NONEFrame, f"pts: {f.pts}, t: {t}"
        return


class TestFrames:

    def test_frames(self):
        fdr = ForcedIDR(nframes=30)
        for f in yield_frames(91):
            fdr.force(f)
            if f.pts in [0, 30, 60, 90]:
                assert f.pict_type == IFrame, f"pts: {f.pts}"
            else:
                assert f.pict_type == NONEFrame, f"pts: {f.pts}"
        #
        fdr = ForcedIDR(nframes=15)
        for f in yield_frames(91):
            fdr.force(f)
            if f.pts % 15 == 0:
                assert f.pict_type == IFrame, f"pts: {f.pts}"
            else:
                assert f.pict_type == NONEFrame, f"pts: {f.pts}"
        #
        fdr = ForcedIDR(nframes=45)
        for f in yield_frames(91):
            fdr.force(f)
            if f.pts % 45 == 0:
                assert f.pict_type == IFrame, f"pts: {f.pts}"
            else:
                assert f.pict_type == NONEFrame, f"pts: {f.pts}"
        return


def main():
    return


if __name__ == "__main__":
    main()
