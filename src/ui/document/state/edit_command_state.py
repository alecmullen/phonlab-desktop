from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EditCommandState:
    """A record of a single edit command, for undo/redo purposes."""

    type: str  # "cut" | "paste"
    start_idx: int
    clip_x: np.ndarray
