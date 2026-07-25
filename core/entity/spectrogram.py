from dataclasses import dataclass

import numpy as np


@dataclass
class Spectrogram:
    t: np.ndarray
    f: np.ndarray
    Sxx: np.ndarray
    