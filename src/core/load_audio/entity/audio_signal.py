from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AudioSignal:
    x: np.ndarray
    fs: int
