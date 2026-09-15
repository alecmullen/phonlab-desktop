from dataclasses import dataclass

from ui.base.state import State


@dataclass
class SelectState(State):
    sel_start: float = 0.0
    sel_end: float = 0.0
    sel_anchor: float = 0.0
    is_selected: bool = False
