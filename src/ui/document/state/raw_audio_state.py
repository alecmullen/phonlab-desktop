from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RawAudioState:
    channels: list[np.ndarray] | None = None
    fs: int | None = None
