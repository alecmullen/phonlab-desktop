import numpy as np

import phonlab as phon
from core.entity.spectrogram import Spectrogram
from core.usecase.use_case import UseCase


class ComputeSpectrogram(UseCase[Spectrogram]):
    def __init__(
        self,
        x: np.ndarray,
        fs: int,
        window_size: float = 0.008,
        step_size: float = 0.002,
        order: int = 9,
    ):
        self.x = x
        self.fs = fs
        self.window_size = window_size
        self.step_size = step_size
        self.order = order

    def invoke(self):
        t, f, sxx = phon.compute_sgram(
            self.x, self.fs, self.window_size, self.step_size, self.order
        )
        yield Spectrogram(t, f, sxx)

    def stop(self):
        pass
