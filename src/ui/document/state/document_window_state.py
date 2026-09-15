from dataclasses import dataclass

from ui.base.state import State


@dataclass
class DocumentWindowState(State):
    start: int = 0
    end: int = 0
    max_start: int = 0
