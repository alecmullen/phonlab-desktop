from dataclasses import dataclass

from ui.base.state import State


@dataclass(frozen=True)
class AnnotationSelectedState(State):
    sel_start: float
    sel_end: float
