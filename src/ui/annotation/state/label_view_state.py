from dataclasses import dataclass

from ui.base.state import State


@dataclass(frozen=True)
class LabelViewState(State):
    size: tuple
    pos: tuple
    label: str
