from dataclasses import dataclass

from ui.base.state import State


@dataclass(frozen=True)
class SpectrogramWindowState(State):
    start: int = 0
    end: int = 0
