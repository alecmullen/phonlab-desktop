from dataclasses import dataclass

from ui.base.state import State


@dataclass
class LoadProgressState(State):
    is_loading: bool = False
