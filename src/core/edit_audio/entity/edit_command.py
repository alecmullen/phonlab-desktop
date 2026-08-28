from dataclasses import dataclass

import numpy as np


@dataclass
class EditCommand:
    kind: str  # "cut" | "paste"
    raw_position: int
    raw_samples: np.ndarray  # removed (cut) or inserted (paste) native-rate samples
