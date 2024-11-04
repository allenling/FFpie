


import fractions


class FakeFrame:

    def __init__(self, pts=0, tb=None, duration=1):
        self.pts = pts
        self.time_base = tb or fractions.Fraction(1, 30)
        self.key_frame = True
        self.pict_type = None
        self.duration = duration
        return

    def __str__(self):
        return f"Frame<{self.pts},{self.time_base}>"

    def __repr__(self):
        return self.__str__()

    @property
    def time(self):
        return float(self.pts*self.time_base) if self.time_base else None


def yield_frames(n):
    f = FakeFrame()
    for i in range(n):
        f.pts = i
        yield f
    return


def yield_frames_st_ed(st, ed):
    f = FakeFrame()
    for i in range(st, ed):
        f.pts = i
        yield f
    return


def yield_with_keyframe(ed, st=0):
    for f in yield_frames_st_ed(st, ed):
        if f.pts % 30 == 0:
            f.key_frame = True
        else:
            f.key_frame = False
        yield f
    return


def main():
    return


if __name__ == "__main__":
    main()
