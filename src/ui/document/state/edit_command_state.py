from dataclasses import dataclass

import numpy as np

from ui.base.state import State


@dataclass(frozen=True)
class EditCommandState(State):
    """A record of a single edit command, for undo/redo purposes."""

    type: str  # "cut" | "paste"
    start_idx: int
    clip_x: np.ndarray
