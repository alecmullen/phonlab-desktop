from dataclasses import dataclass

from ui.base.state import State


@dataclass(frozen=True)
class ChannelActiveState(State):
    is_active: bool = True
