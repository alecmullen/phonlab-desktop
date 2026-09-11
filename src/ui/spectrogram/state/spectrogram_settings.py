from dataclasses import dataclass

import numpy as np

from ui.base.state import State


@dataclass(frozen=True)
class SpectrogramSettingsState(State):
    fs: int = 16000
    window_size: float = 0.008
    step_size: float = 0.001
    order: int = 9

    def __post_init__(self):
        nperseg = int(self.window_size * self.fs)
        minimum_order = np.floor(np.log2(nperseg)) + 1
        object.__setattr__(self, "order", max(self.order, minimum_order))
