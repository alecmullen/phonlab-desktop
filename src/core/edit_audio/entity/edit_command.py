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
