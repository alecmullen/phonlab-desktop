from dataclasses import dataclass, field

import numpy as np

from core.track_formants.entity.formant_track import FormantTrack
from ui.base.state import State


@dataclass(frozen=True)
class FormantTrackState(State):
    """Formant dots to draw: `sec` is absolute time in the document and
    `formants` has shape (frames, 4), in Hz."""

    sec: np.ndarray = field(default_factory=lambda: np.zeros(0))
    formants: np.ndarray = field(default_factory=lambda: np.zeros((0, 4)))


def to_formant_track_state(track: FormantTrack, offset: float) -> FormantTrackState:
    return FormantTrackState(track.sec + offset, track.formants)
