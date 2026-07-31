from dataclasses import dataclass, field

import numpy as np

from core.entity.spectrogram import Spectrogram


@dataclass
class SpectrogramState:
    t: np.ndarray = field(default_factory=lambda: np.zeros(0))
    f: np.ndarray = field(default_factory=lambda: np.zeros(0))
    sxx: np.ndarray = field(default_factory=lambda: np.zeros(0))
    is_showing: bool = False

def to_spectrogram_model(spectrogram: Spectrogram, start: float):
    return SpectrogramState(np.add(spectrogram.t, start), spectrogram.f, spectrogram.sxx, is_showing=True)
