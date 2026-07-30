from dataclasses import dataclass, field

import numpy as np


@dataclass
class FullAudioState:
    x: np.ndarray = field(default_factory=lambda: np.zeros(0))
    fs: float = 0.0
