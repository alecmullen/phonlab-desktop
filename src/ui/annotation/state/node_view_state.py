from dataclasses import dataclass

from ui.base.state import State


@dataclass(frozen=True)
class NodeTierExtent(State):
    tier: int
    has_point_label: bool = False


@dataclass(frozen=True)
class NodeViewState(State):
    node: int
    x: float
    extents: list[NodeTierExtent]
