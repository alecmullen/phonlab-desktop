from dataclasses import dataclass

from ui.base.state import State


@dataclass(frozen=True)
class ChannelActiveState(State):
    idx: int = 0
    is_active: bool = True
