from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class SpectrogramState:
    f: np.ndarray = field(default_factory=lambda: np.zeros(0))

    t_window: np.ndarray = field(default_factory=lambda: np.zeros(0))
    sxx_window: np.ndarray = field(default_factory=lambda: np.zeros(0))

    t_mmap: np.memmap | None = None
    sxx_mmap: np.memmap | None = None
    frames_per_sec: float = 0.0
    frames_computed: int = 0
    samples_computed: int = 0

    is_showing: bool = False
