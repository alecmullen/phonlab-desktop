from dataclasses import dataclass, field

import numpy as np


@dataclass
class WaveformState:
    x: np.ndarray = field(default_factory=lambda: np.zeros(0))
    fs: int = 0
    min_x: float = 0.0
    max_x: float = 0.0
    t: np.ndarray = field(default_factory=lambda: np.zeros(0))


def to_waveform_state(x: np.ndarray, fs: int) -> WaveformState:
    min_x = float(np.min(x))
    max_x = float(np.max(x))
    t = np.arange(len(x)) / fs

    return WaveformState(x, fs, min_x, max_x,  t)
