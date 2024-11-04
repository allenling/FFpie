

import cv2 as cv

import ffpie

FPATH = r"D:\Downloads\yellowstone.mp4"



def read_frames():
    s1 = ffpie.Source(FPATH)
    for af in s1.read_audio_frames():
        print(af, af.time)
    s1.seek(0)
    for vf in s1.read_video_frames():
        cv_frame = vf.to_ndarray(format='bgr24')
        cv.imshow("12", cv_frame)
        cv.waitKey(1)
    return


def hardware_decoder():
    s1 = ffpie.H264HWSource(FPATH)
    s1.seek(10.2, 15)
    for frame in s1.read_video_frames():
        cv_frame = frame.to_ndarray(format='bgr24')
        cv.imshow("12", cv_frame)
        cv.waitKey(1)
    s1.seek(0)
    for frame in s1.read_video_frames():
        cv_frame = frame.to_ndarray(format='bgr24')
        cv.imshow("12", cv_frame)
        cv.waitKey(1)
    s1.close()
    return


def main():
    # read_frames()
    hardware_decoder()
    return


if __name__ == "__main__":
    main()

