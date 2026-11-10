import numpy as np
import phonlab as phon

from core.base.use_case import UseCase
from core.spectrogram.entity.spectrogram import Spectrogram


class ComputeSpectrogram(UseCase[Spectrogram]):
    def __call__(
        self,
        x: np.ndarray,
        fs: int,
        window_size: float = 0.008,
        step_size: float = 0.001,
        order: int = 9,
    ):
        t, f, sxx = phon.compute_sgram(x, fs, window_size, step_size, order)
        yield Spectrogram(t, f, sxx)
