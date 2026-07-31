from dataclasses import dataclass


@dataclass
class SelectState:
    sel_start: float = 0.0
    sel_end: float = 0.0
    sel_anchor: float = 0.0
    is_selected: bool = False
