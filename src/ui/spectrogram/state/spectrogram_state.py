from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np

from res.constants import DEFAULT_GRAY_CUTOFF
from ui.base.state import State


class SpectrogramUnavailable(StrEnum):
    """Why there is no spectrogram for the window being looked at"""

    TOO_LONG = "too_long"
    TOO_SHORT = "too_short"


class FrequencyScale(StrEnum):
    """How the rows of the spectrogram are spaced in frequency"""

    HZ = "hz"  # evenly
    MEL = "mel"  # evenly on the mel scale, so closer together at the top


@dataclass(frozen=True)
class SpectrogramState(State):
    # The frequency of each row of the spectrogram, in Hz
    f: np.ndarray = field(default_factory=lambda: np.zeros(0))
    frequency_scale: FrequencyScale = FrequencyScale.HZ

    t_window: np.ndarray = field(default_factory=lambda: np.zeros(0))
    sxx_window: np.ndarray = field(default_factory=lambda: np.zeros(0))

    t_mmap: np.memmap | None = None
    sxx_mmap: np.memmap | None = None
    frames_per_sec: float = 0.0
    frames_computed: int = 0
    samples_computed: int = 0

    is_showing: bool = False
    is_loading: bool = True
    unavailable: SpectrogramUnavailable | None = None

    gray_cutoff: float = DEFAULT_GRAY_CUTOFF
    low_sxx: float = float("inf")
    high_sxx: float = float("-inf")
