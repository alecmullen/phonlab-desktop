from dataclasses import dataclass, field

from core.parse_textgrid.annotation import Annotation
from ui.annotation.state.annotation_state import (
    AnnotationState,
    to_annotation_state,
    update_annotation_state_from_window,
)
from ui.base.state import State


@dataclass(frozen=True)
class AnnotationWindowState(State):
    annotation_state: AnnotationState = field(default_factory=lambda: AnnotationState())
    start: float = 0.0
    end: float = 0.0


def update_annotation_window_state(
    annotation_state: AnnotationState, start: float, end: float
) -> AnnotationWindowState:
    return AnnotationWindowState(
        update_annotation_state_from_window(annotation_state, start, end),
        start,
        end,
    )


def to_annotation_window_state(
    annotation: Annotation, start: float, end: float
) -> AnnotationWindowState:
    annotation_state = to_annotation_state(annotation)
    return AnnotationWindowState(
        update_annotation_state_from_window(annotation_state, start, end),
        start,
        end,
    )
