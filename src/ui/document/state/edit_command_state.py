from dataclasses import dataclass

import numpy as np

from ui.base.state import State


@dataclass(frozen=True)
class EditCommandState(State):
    """A record of a single edit command, for undo/redo purposes."""

    type: str  # "cut" | "paste" | "replace"
    start_idx: int
    clips: dict[int, np.ndarray]  # one entry per channel touched (1 mono, 2 stereo)
    # "replace" only: the samples that `clips` overwrote (same length as `clips`)
    previous: dict[int, np.ndarray] | None = None
