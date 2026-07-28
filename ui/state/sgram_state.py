from dataclasses import dataclass

import numpy as np

from core.entity.spectrogram import Spectrogram


@dataclass
class SpectrogramState:
    t: np.ndarray
    f: np.ndarray
    sxx: np.ndarray
    duration: float
    total_duration: float

def to_spectrogram_model(sgram: Spectrogram, start: float, duration: float, total_duration: float):
    return SpectrogramState(np.add(sgram.t, start), sgram.f, sgram.sxx, duration, total_duration)
