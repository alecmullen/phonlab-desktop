from dataclasses import dataclass
from enum import Enum

from core.track_formants.entity.formant_method import FormantMethod
from res.constants import (
    FORMANT_AUTO_ORDER,
    FORMANT_DELTA_F,
    FORMANT_MEDIAN_F0,
    FORMANT_PREEMPHASIS,
    FORMANT_TOP_FREQUENCY,
)


class FormantSpeakerType(Enum):
    LONG = 0
    MEDIUM = 1
    SHORT = 2


@dataclass(frozen=True)
class FormantOptions:
    """How to track formants: the method and the parameters it uses. Each
    method reads only some of them:

    - IFC: preemphasis, speaker
    - LPC: preemphasis, order
    - RLPC: preemphasis, order, top_frequency
    - TVLP: preemphasis, order, top_frequency, median_f0
    - DPPT: preemphasis, delta_f

    An `order` below 1 means phonlab picks the LPC order."""

    method: FormantMethod = FormantMethod.IFC
    preemphasis: float = FORMANT_PREEMPHASIS["ifc"]
    speaker: FormantSpeakerType = FormantSpeakerType.MEDIUM
    order: int = FORMANT_AUTO_ORDER
    top_frequency: int = FORMANT_TOP_FREQUENCY
    median_f0: float = FORMANT_MEDIAN_F0
    delta_f: int = FORMANT_DELTA_F
