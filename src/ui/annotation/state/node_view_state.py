from dataclasses import dataclass

from ui.base.state import State


@dataclass(frozen=True)
class NodeViewState(State):
    x: float
    ys: list[float]
