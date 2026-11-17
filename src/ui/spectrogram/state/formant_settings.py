from dataclasses import dataclass, replace
from enum import StrEnum

from core.track_formants.entity.formant_method import FormantMethod
from core.track_formants.entity.formant_options import (
    FormantOptions,
    FormantSpeakerType,
)
from res.constants import (
    FORMANT_AUTO_ORDER,
    FORMANT_DELTA_F,
    FORMANT_MEDIAN_F0,
    FORMANT_PREEMPHASIS,
    FORMANT_TOP_FREQUENCY,
)
from ui.base.state import State


class FormantMethodState(StrEnum):
    """Mirrors core's FormantMethod"""

    IFC = "ifc"
    LPC = "lpc"
    RLPC = "rlpc"
    TVLP = "tvlp"
    DPPT = "dppt"


@dataclass(frozen=True)
class FormantSettingsState(State):
    """Formant tracking settings. Which of them the dialog offers, and which
    the tracker reads, depends on the method (see core's FormantOptions)."""

    method: FormantMethodState = FormantMethodState.IFC
    preemphasis: float = FORMANT_PREEMPHASIS["ifc"]
    speaker: FormantSpeakerType = FormantSpeakerType.MEDIUM
    order: int = FORMANT_AUTO_ORDER
    top_frequency: int = FORMANT_TOP_FREQUENCY
    median_f0: int = FORMANT_MEDIAN_F0
    delta_f: int = FORMANT_DELTA_F

    def with_method(self, method: FormantMethodState) -> "FormantSettingsState":
        """These settings for another method, with its usual preemphasis"""
        return replace(
            self, method=method, preemphasis=FORMANT_PREEMPHASIS[method.value]
        )


def to_formant_options(settings: FormantSettingsState) -> FormantOptions:
    return FormantOptions(
        method=FormantMethod(settings.method.value),
        preemphasis=settings.preemphasis,
        speaker=settings.speaker,
        order=settings.order,
        top_frequency=settings.top_frequency,
        median_f0=settings.median_f0,
        delta_f=settings.delta_f,
    )
