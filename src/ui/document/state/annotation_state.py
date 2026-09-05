from dataclasses import dataclass, field

from ui.base.state import State


@dataclass(frozen=True)
class AnnotationLabelState(State):
    s_node: int
    e_node: int
    label: str


@dataclass(frozen=True)
class AnnotationTypeState(State):
    type: str
    labels: list[AnnotationLabelState]


@dataclass(frozen=True)
class AnnotationState(State):
    nodes: dict[int, float] = field(default_factory=dict)
    types: list[AnnotationTypeState] = field(default_factory=list)
