

class FrameSampler:
    video = False
    audio = False
    flushed = False

    def sample(self, frame):
        raise NotImplementedError

    def flush(self):
        for frame in self.sample(None):
            yield frame
        return


class AudioFrameSampler(FrameSampler):

    audio = True

    def sample(self, frame):
        raise NotImplementedError

    def flush_to_oc(self, oc):
        for frame in self.flush():
            oc.mux_one_audio_frame(frame)
        return


class VideoFrameSampler(FrameSampler):

    fps_mode = None
    video = True

    def sample(self, frame):
        raise NotImplementedError

    def flush_to_oc(self, oc):
        for frame in self.flush():
            oc.mux_one_video_frame(frame)
        return


def main():
    return


if __name__ == "__main__":
    main()
