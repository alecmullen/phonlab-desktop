from dataclasses import dataclass
from enum import StrEnum

from core.load_audio.entity.audio_signal import AudioSignal


class EditCommandType(StrEnum):
    CUT = "cut"
    PASTE = "paste"
    COPY = "copy"
    REPLACE = "replace"


@dataclass
class EditCommand:
    type: EditCommandType
    start_time: float
    end_time: float | None = None
    clip: dict[int, AudioSignal] | None = None
    # REPLACE only: exact sample index to overwrite from (no time conversion or
    # zero-crossing snapping, so an undo lands on the same samples)
    start_idx: int | None = None
