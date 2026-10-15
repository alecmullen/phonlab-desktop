from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FormantTrack:
    """Formant measurements of an audio clip. `sec` is the time of each frame
    in seconds from the start of the clip; `formants` has shape (frames, 4),
    one column each for F1-F4 in Hz."""

    sec: np.ndarray
    formants: np.ndarray
