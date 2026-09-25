from dataclasses import dataclass, field

from core.parse_textgrid.annotation import Annotation
from ui.annotation.state.annotation_label_state import (
    AnnotationLabelState,
    update_label_state,
)
from ui.annotation.state.annotation_node_state import (
    AnnotationNodeExtentState,
    AnnotationNodeState,
    to_node_state,
)
from ui.base.state import State


@dataclass(frozen=True)
class AnnotationTypeState(State):
    type: str
    labels: list[AnnotationLabelState]


@dataclass(frozen=True)
class AnnotationState(State):
    nodes: dict[int, AnnotationNodeState] = field(default_factory=dict)
    types: list[AnnotationTypeState] = field(default_factory=list)


def to_annotation_state(annotation: Annotation) -> AnnotationState:
    return AnnotationState(
        nodes={
            node: AnnotationNodeState(node, x) for node, x in annotation.nodes.items()
        },
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


def update_annotation_state_from_window(
    annotation: AnnotationState, start: float, end: float
) -> AnnotationState:

    types = []
    node_extents = {node: set[AnnotationNodeExtentState]() for node in annotation.nodes}

    for tier, type in enumerate(annotation.types):
        labels = []
        for label in type.labels:
            label_state = update_label_state(
                label,
                start,
                end,
                annotation.nodes[label.s_node].x,
                annotation.nodes[label.e_node].x,
                tier,
            )
            labels.append(label_state)

            if label_state.is_visible:
                is_point = label.s_node == label.e_node

                node_extents[label.s_node] = update_extent_set(
                    node_extents[label.s_node], tier, is_point
                )
                node_extents[label.e_node] = update_extent_set(
                    node_extents[label.e_node], tier, is_point
                )

        types.append(AnnotationTypeState(type.type, labels))

    nodes = {}
    for node in annotation.nodes.values():
        node_state = to_node_state(
            node.node, node.x, node_extents[node.node], start, end
        )
        nodes[node.node] = node_state

    return AnnotationState(nodes=nodes, types=types)


def update_extent_set(
    extents: set[AnnotationNodeExtentState], tier: int, is_point: bool
) -> set[AnnotationNodeExtentState]:
    extents = extents.copy()

    for extent in extents:
        if extent.tier == tier:
            extents.remove(extent)
            extents.add(
                AnnotationNodeExtentState(tier, extent.has_point_label or is_point)
            )
            return extents

    extents.add(AnnotationNodeExtentState(tier, is_point))
    return extents
