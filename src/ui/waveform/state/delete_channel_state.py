from dataclasses import dataclass

from ui.base.state import State


@dataclass(frozen=True)
class DeleteChannelState(State):
    idx: int = 0
