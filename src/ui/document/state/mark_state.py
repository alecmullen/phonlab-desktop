from dataclasses import dataclass

from ui.base.state import State


@dataclass
class MarkState(State):
    position: float = 0.0  # seconds
    is_set: bool = False
