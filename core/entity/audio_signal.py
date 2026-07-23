from dataclasses import dataclass
import numpy as np

@dataclass
class AudioSignal:
    y: np.ndarray
    fs: int
    