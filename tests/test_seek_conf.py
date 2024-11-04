

from ffpie.source import SeekConf


from tests.common import yield_with_keyframe


class TestSeekConf:

    def test_seek(self):
        s = SeekConf()
        for f in yield_with_keyframe(100):
            assert s.check_in_range(f.key_frame, f.pts) is True
        return

    def test_end(self):
        ed = 2.5
        s = SeekConf(end=ed)
        for f in yield_with_keyframe(100):
            t = f.time
            ret = s.check_in_range(f.key_frame, t)
            if t <= ed:
                assert ret is True, f"!{f.pts}, {t}"
            else:
                assert ret is None
        return

    def test_start_end(self):
        st, ed = 2.1, 3.5
        s = SeekConf(start=st, end=ed)
        for f in yield_with_keyframe(120):
            t = f.time
            ret = s.check_in_range(f.key_frame, t)
            if t < st:
                assert ret is False
            elif st <= t <= ed:
                assert ret is True
            else:
                assert ret is None
        return

    def test_leftmost_rightmost(self):
        st, ed = 2.3, 3.5
        s = SeekConf(start=st, end=ed, leftmost=True, rightmost=True)
        leftmost = 2
        rigmost = 4
        for f in yield_with_keyframe(st=60, ed=150):
            t = f.time
            ret = s.check_in_range(f.key_frame, t)
            if leftmost <= t <= rigmost:
                assert ret is True
            else:
                assert ret is None
        return

    def test_exclusive_end(self):
        st, ed = 2.3, 3.5
        s = SeekConf(start=st, end=ed, exclusive_end=False)
        prevt = None
        first_none = False
        for f in yield_with_keyframe(st=60, ed=150):
            t = f.time
            ret = s.check_in_range(f.key_frame, t)
            if t < st:
                assert ret is False
            elif st <= t <= ed:
                assert ret is True
            else:
                if first_none is False:
                    assert prevt == ed
                    first_none = True
                assert ret is None
            prevt = t
        #
        s = SeekConf(start=st, end=ed, exclusive_end=True)
        first_none = False
        for f in yield_with_keyframe(st=60, ed=150):
            t = f.time
            ret = s.check_in_range(f.key_frame, t)
            if t < st:
                assert ret is False
            elif st <= t < ed:
                assert ret is True
            else:
                if first_none is False:
                    assert prevt == ed - 1/30
                    first_none = True
                assert ret is None
            prevt = t
        return



def main():
    return


if __name__ == "__main__":
    main()
