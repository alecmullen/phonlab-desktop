from dataclasses import dataclass


@dataclass(frozen=True)
class AnnotationLabelState:
    s_node: int
    e_node: int
    label: str


@dataclass(frozen=True)
class AnnotationTypeState:
    type: str
    labels: list[AnnotationLabelState]


@dataclass(frozen=True)
class AnnotationState:
    nodes: dict[int, float]
    types: list[AnnotationTypeState]
