import numpy as np

from core.base.use_case import UseCase
from core.spectrogram.entity.spectrogram import Spectrogram
from core.spectrogram.entity.spectrogram_type import SpectrogramType
from core.spectrogram.typed_sgram import compute_typed_sgram


class ComputeSpectrogram(UseCase[Spectrogram]):
    def __call__(
        self,
        x: np.ndarray,
        fs: int,
        window_size: float = 0.008,
        step_size: float = 0.001,
        order: int = 9,
        sgram_type: SpectrogramType = SpectrogramType.FFT,
    ):
        t, f, sxx = compute_typed_sgram(
            x, fs, sgram_type, window_size, step_size, order
        )
        yield Spectrogram(t, f, sxx)
