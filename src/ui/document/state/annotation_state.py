from dataclasses import dataclass, field


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
    nodes: dict[int, float] = field(default_factory=dict)
    types: list[AnnotationTypeState] = field(default_factory=list)
