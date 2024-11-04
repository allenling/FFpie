

from fractions import Fraction


from ffpie.ffutils import adjust_frame_pts_to_encoder_tb

from tests.common import FakeFrame


def test_adjust(monkeypatch):
    tb_out = Fraction(1001, 30000)
    start_time = 0
    const = 1/(1 << 17)
    expections = [0, 0.5+const, 1, 1.5+const, 2, 2.5+const, 5]
    for idx, pts in enumerate([0, 1001, 2002, 3003, 4004, 5005, 10010]):
        frame = FakeFrame(pts, tb=Fraction(1, 60000))
        ret = adjust_frame_pts_to_encoder_tb(frame, tb_out, start_time)
        assert ret == expections[idx], (idx, ret, expections[idx])
    return



def main():
    return


if __name__ == "__main__":
    main()
