from dataclasses import dataclass
from enum import Enum

from core.track_formants.entity.formant_method import FormantMethod
from res.constants import (
    FORMANT_AUTO_ORDER,
    FORMANT_DELTA_F,
    FORMANT_LENGTH_SEC,
    FORMANT_MEDIAN_F0,
    FORMANT_PREEMPHASIS,
    FORMANT_STEP_SEC,
    FORMANT_TOP_FREQUENCY,
    FORMANT_VOICING_THRESHOLD,
)


class FormantSpeakerType(Enum):
    LONG = 0
    MEDIUM = 1
    SHORT = 2


@dataclass(frozen=True)
class FormantOptions:
    """How to track formants: the method and the parameters it uses. Each
    method reads only some of them:

    - IFC: preemphasis, speaker (it measures every 10 ms, with no length)
    - LPC: preemphasis, order, step, length
    - RLPC: preemphasis, order, top_frequency, step, length
    - TVLP: preemphasis, order, top_frequency, median_f0, step, length
    - DPPT: preemphasis, delta_f, step, length

    An `order` below 1 means phonlab picks the LPC order. `step` and `length`
    are in seconds. With `voiced_only`, the formants of frames that phon.VAD()
    does not find voiced (a probability above `voicing_threshold`) are NaN."""

    method: FormantMethod = FormantMethod.IFC
    preemphasis: float = FORMANT_PREEMPHASIS["ifc"]
    speaker: FormantSpeakerType = FormantSpeakerType.MEDIUM
    order: int = FORMANT_AUTO_ORDER
    top_frequency: int = FORMANT_TOP_FREQUENCY
    median_f0: float = FORMANT_MEDIAN_F0
    delta_f: int = FORMANT_DELTA_F
    step: float = FORMANT_STEP_SEC
    length: float = FORMANT_LENGTH_SEC["ifc"]
    voiced_only: bool = False
    voicing_threshold: float = FORMANT_VOICING_THRESHOLD
