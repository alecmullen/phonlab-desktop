from dataclasses import dataclass

import numpy as np

from core.entity.spectrogram import Spectrogram


@dataclass
class SpectrogramState:
    t: np.ndarray
    f: np.ndarray
    Sxx: np.ndarray
    duration: float
    total_duration: float

def to_spectrogram_model(sgram: Spectrogram, duration: float, total_duration: float):
    return SpectrogramState(sgram.t, sgram.f, sgram.Sxx, duration, total_duration)
