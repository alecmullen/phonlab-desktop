import numpy as np


class FakeAudioPlayer:
    """Stands in for `AudioPlayer` so no audio device is touched"""

    def __init__(self):
        self.stopped = False
        self.played: list[tuple[np.ndarray, int, float]] = []

    def stop(self):
        self.stopped = True

    def play(self, x: np.ndarray, fs: int, start: float):
        self.played.append((x, fs, start))

    class playback_poll:
        @staticmethod
        def connect(slot: object):
            pass
