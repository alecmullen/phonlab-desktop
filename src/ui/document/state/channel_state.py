from dataclasses import dataclass

from ui.base.state import State


@dataclass(frozen=True)
class ChannelState(State):
    primary_channel: int = 0
    channel_mode: str = ""
