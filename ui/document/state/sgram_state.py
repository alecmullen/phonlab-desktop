from dataclasses import dataclass, field

import numpy as np

from core.entity.spectrogram import Spectrogram


@dataclass(frozen=True)
class SpectrogramState:
    f: np.ndarray = field(default_factory=lambda: np.zeros(0))

    t_window: np.ndarray = field(default_factory=lambda: np.zeros(0))
    sxx_window: np.ndarray = field(default_factory=lambda: np.zeros(0))

    start_buffer: int = 0
    end_buffer: int = 0
    t_buffer: np.ndarray = field(default_factory=lambda: np.zeros(0))
    sxx_buffer: np.ndarray = field(default_factory=lambda: np.zeros(0))

    t_mmap: np.memmap | None = None
    sxx_mmap: np.memmap | None = None

    is_showing: bool = False
