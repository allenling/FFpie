

import math

from fractions import Fraction


from ffpie.constants import AV_TIME_BASE_Q



def av_clip(val, min_v, max_v):
    if val < min_v:
        return min_v
    if val > max_v:
        return max_v
    return int(val)


def av_rescale_q_near_inf(x: float, tb1: Fraction, tb2: Fraction):
    # AV_ROUND_NEAR_INF mode
    num1 = tb1.numerator
    den1 = tb1.denominator
    num2 = tb2.numerator
    den2 = tb2.denominator
    a = x
    b = num1 * den2
    c = num2 * den1
    ret = a*b / c + 0.5
    return int(ret)


def ffsign(x):
    return 1 if x > 0 else -1


def llrintf(val):
    return round(val)


def llrint(val):
    return llrintf(val)


def adjust_frame_pts_to_encoder_tb(frame, tb_out: Fraction, start_time: float):
    filter_tb = frame.time_base
    extra_bits = av_clip(29 - int(math.log2(tb_out.denominator)), 0, 16)
    tmp_tb = Fraction(tb_out.numerator, tb_out.denominator << extra_bits)
    a = av_rescale_q_near_inf(frame.pts, filter_tb, tmp_tb)
    b = av_rescale_q_near_inf(start_time, AV_TIME_BASE_Q, tmp_tb)
    float_pts = a - b
    float_pts /= 1 << extra_bits
    if float_pts != llrint(float_pts):
        float_pts += ffsign(float_pts) * 1.0 / (1 << 17)
    frame.time_base = tb_out
    return float_pts


def main():
    return


if __name__ == "__main__":
    main()
