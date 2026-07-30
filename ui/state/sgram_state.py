from dataclasses import dataclass, field

import numpy as np

from core.entity.spectrogram import Spectrogram


@dataclass
class SpectrogramState:
    t: np.ndarray = field(default_factory=lambda: np.zeros(0))
    f: np.ndarray = field(default_factory=lambda: np.zeros(0))
    sxx: np.ndarray = field(default_factory=lambda: np.zeros(0))
    duration: float = 0.0
    total_duration: float = 0.0

def to_spectrogram_model(sgram: Spectrogram, start: float, duration: float, total_duration: float):
    return SpectrogramState(np.add(sgram.t, start), sgram.f, sgram.sxx, duration, total_duration)
