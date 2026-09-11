from dataclasses import dataclass, field

import numpy as np

from res.constants import DEFAULT_GRAY_CUTOFF
from ui.base.state import State


@dataclass(frozen=True)
class SpectrogramState(State):
    f: np.ndarray = field(default_factory=lambda: np.zeros(0))

    t_window: np.ndarray = field(default_factory=lambda: np.zeros(0))
    sxx_window: np.ndarray = field(default_factory=lambda: np.zeros(0))

    t_mmap: np.memmap | None = None
    sxx_mmap: np.memmap | None = None
    frames_per_sec: float = 0.0
    frames_computed: int = 0
    samples_computed: int = 0

    is_showing: bool = False
    is_loading: bool = True

    gray_cutoff: float = DEFAULT_GRAY_CUTOFF
    min_sxx: float = float("inf")
    max_sxx: float = float("-inf")
