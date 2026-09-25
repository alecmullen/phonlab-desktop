from dataclasses import dataclass, field

from ui.base.state import State


@dataclass(frozen=True)
class AnnotationNodeExtentState(State):
    tier: int = 0
    has_point_label: bool = False


@dataclass(frozen=True)
class AnnotationNodeState(State):
    node: int = 0
    x: float = 0.0
    extents: list[AnnotationNodeExtentState] = field(default_factory=list)

    is_visible: bool = False


def to_node_state(
    node: int,
    x: float,
    extents: set[AnnotationNodeExtentState],
    start: float,
    end: float,
) -> AnnotationNodeState:
    return AnnotationNodeState(
        node,
        x,
        sorted(extents, key=lambda extent: extent.tier),
        start <= x and end >= x and len(extents) > 0,
    )
