from dataclasses import dataclass
from enum import StrEnum

import numpy as np


class EditCommandType(StrEnum):
    CUT = "cut"
    PASTE = "paste"
    COPY = "copy"


@dataclass
class EditCommand:
    type: EditCommandType
    start_time: float
    end_time: float | None = None
    clip_x: np.ndarray | None = None
    clip_fs: int | None = None
    # PASTE only: use this exact sample index instead of recomputing it from
    # start_time (and skip zero-crossing snapping) - lets a stereo pair's two
    # channels insert at identical sample positions, since each channel would
    # otherwise snap independently to its own nearest zero-crossing.
    snapped_start_idx: int | None = None
