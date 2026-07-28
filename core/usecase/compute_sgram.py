import phonlab as phon

from core.entity.spectrogram import Spectrogram
from core.usecase.use_case import UseCase


class ComputeSpectrogram(UseCase):

    def __init__(self, x, fs, window_size=0.008, step_size=0.002, order=9):
        super().__init__()
        self.x = x
        self.fs = fs
        self.window_size = window_size
        self.step_size = step_size
        self.order = order

    def invoke(self) -> Spectrogram:
        t, f, sxx = phon.compute_sgram(self.x, self.fs, self.window_size, self.step_size, self.order)
        return Spectrogram(t, f, sxx)
    