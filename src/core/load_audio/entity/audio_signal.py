from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class AudioSignal:
    x: np.ndarray = field(default_factory=lambda: np.array([]))
    fs: int = 0
