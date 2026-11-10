from dataclasses import dataclass

from res.constants import (
    FORMANT_F0_MAX,
    FORMANT_F0_MIN,
    FORMANT_PREEMPHASIS,
    FORMANT_SPEAKER,
)
from ui.base.state import State


@dataclass(frozen=True)
class FormantSettingsState(State):
    preemphasis: float = FORMANT_PREEMPHASIS
    f0_min: int = FORMANT_F0_MIN
    f0_max: int = FORMANT_F0_MAX
    speaker: int = FORMANT_SPEAKER
