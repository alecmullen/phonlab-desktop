from dataclasses import dataclass
from enum import Enum

from res.constants import FORMANT_PREEMPHASIS
from ui.base.state import State


class FormantSpeakerType(Enum):
    LONG = 0
    MEDIUM = 1
    SHORT = 2


@dataclass(frozen=True)
class FormantSettingsState(State):
    preemphasis: float = FORMANT_PREEMPHASIS
    speaker: FormantSpeakerType = FormantSpeakerType.MEDIUM
