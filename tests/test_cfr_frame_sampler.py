

from fractions import Fraction


import ffpie

from tests.common import FakeFrame


out_fps = Fraction(30000, 1001)


def test_cfr():
    exp_nb_frames = [1, 1, 1, 1, 1, 0, 1, 0]
    exp_pts = [0, 1, 2, 3, 4, None, 5]
    cfr = ffpie.CFRSampler(out_fps=out_fps)
    for idx, pts in enumerate([0, 1001, 2002, 3003, 4004, 5005, 6006, 7007]):
        frame = FakeFrame(pts, tb=Fraction(1, 60000), duration=2002)
        outidx = -1
        for outidx, outframe in enumerate(cfr.sample(frame)):
            assert outframe.pts == exp_pts[idx]
        assert outidx == exp_nb_frames[idx] - 1
    return


def test_cfr_nb0_frames():
    tb_out = Fraction(1001, 30000)
    exp_nb_frames = [1, 5]
    exp_pts = [[0], [1, 2, 3, 4, 5]]
    exp_pkt_dts = [[0], [0, 0, 0, 2002, 2002]]
    pkt_dts = [0, 2002]
    input_pts = [0, 10010]
    cfr = ffpie.CFRSampler(out_fps=out_fps)
    for idx, pts in enumerate(input_pts):
        frame = FakeFrame(pts, tb=Fraction(1, 60000), duration=2002)
        frame.pkt_dts = pkt_dts[idx]
        outidx = -1
        for outidx, outframe in enumerate(cfr.sample(frame)):
            assert outframe.pts == exp_pts[idx][outidx]
            assert outframe.pkt_dts == exp_pkt_dts[idx][outidx]
        assert outidx == exp_nb_frames[idx] - 1
    return


def main():
    return


if __name__ == "__main__":
    main()
