from dataclasses import dataclass, field

from ui.base.state import State


@dataclass(frozen=True)
class ChannelState(State):
    primary_channel: int = 0
    channel_mode: str = ""
    active_channels: frozenset[int] = field(default_factory=lambda: frozenset({0}))
