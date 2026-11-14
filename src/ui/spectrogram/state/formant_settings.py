from dataclasses import dataclass

from res.constants import FORMANT_PREEMPHASIS, FORMANT_SPEAKER
from ui.base.state import State


@dataclass(frozen=True)
class FormantSettingsState(State):
    preemphasis: float = FORMANT_PREEMPHASIS
    speaker: int = FORMANT_SPEAKER
