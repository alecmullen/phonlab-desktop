from dataclasses import dataclass


@dataclass
class ZoomToSelection:
    sel_start: float = 0.0
    sel_end: float = 0.0
