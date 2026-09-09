from dataclasses import dataclass, field

from core.parse_textgrid.annotation import Annotation
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


def to_annotation_state(annotation: Annotation) -> AnnotationState:
    return AnnotationState(
        nodes=annotation.nodes,
        types=[
            AnnotationTypeState(
                type.type,
                [
                    AnnotationLabelState(label.s_node, label.e_node, label.label)
                    for label in type.labels
                ],
            )
            for type in annotation.types
        ],
    )
