from dataclasses import dataclass, field

from ui.base.state import State


@dataclass(frozen=True)
class AnnotationLabel(State):
    s_node: int
    e_node: int
    label: str


@dataclass(frozen=True)
class AnnotationType(State):
    type: str
    labels: list[AnnotationLabel]


@dataclass(frozen=True)
class Annotation(State):
    nodes: dict[int, float] = field(default_factory=dict)
    types: list[AnnotationType] = field(default_factory=list)
