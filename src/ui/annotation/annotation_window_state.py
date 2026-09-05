from dataclasses import dataclass, field

from ui.base.state import State
from ui.document.state.annotation_state import AnnotationState


@dataclass(frozen=True)
class AnnotationWindowState(State):
    annotation_state: AnnotationState = field(default_factory=lambda: AnnotationState())
    start: float = 0.0
    end: float = 0.0
