
from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelState:
    primary_channel: int = 0
    channel_mode: str = ""
    