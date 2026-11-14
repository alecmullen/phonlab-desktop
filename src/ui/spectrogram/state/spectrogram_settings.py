from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from res.constants import (
    MEL_MIN_TOP_FREQUENCY,
    SPECTROGRAM_STEP_SEC,
    SPECTROGRAM_WINDOW_SEC,
)
from ui.base.state import State


class SpectrogramTypeState(StrEnum):
    """The kinds of spectrogram the user can choose between"""

    FFT = "fft"
    MULTITAPER = "multitaper"
    CEPSTRAL = "cepstral"
    LPC = "lpc"
    MEL = "mel"


@dataclass(frozen=True)
class SpectrogramSettingsState(State):
    fs: int = 16000
    window_size: float = 0.008
    step_size: float = 0.001
    order: int = 9
    type: SpectrogramTypeState = SpectrogramTypeState.FFT

    def __post_init__(self):
        if self.type == SpectrogramTypeState.MEL:
            # Its filters reach 7600 Hz, which a lower sample rate cannot hold
            object.__setattr__(self, "fs", max(self.fs, 2 * MEL_MIN_TOP_FREQUENCY))
        nperseg = int(self.window_size * self.fs)
        minimum_order = int(np.floor(np.log2(nperseg))) + 1
        object.__setattr__(self, "order", max(int(self.order), minimum_order))

    def with_type(self, type: SpectrogramTypeState) -> "SpectrogramSettingsState":
        """These settings for another type of spectrogram, with that type's
        usual window and step in place of the current ones. (The FFT order is
        worked out afresh from the new window.)"""
        return SpectrogramSettingsState(
            fs=self.fs,
            window_size=SPECTROGRAM_WINDOW_SEC[type],
            step_size=SPECTROGRAM_STEP_SEC[type],
            type=type,
        )
