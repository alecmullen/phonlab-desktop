from dataclasses import dataclass, field
from enum import StrEnum


class ChannelMode(StrEnum):
    MONO = "mono"
    STEREO = "stereo"
    MULTICHANNEL = "multichannel"


@dataclass
class AudioOpenOptions:
    target_fs: int = 16000
    channel_mode: ChannelMode = ChannelMode.MONO
    retained_channels: list[int] = field(default_factory=lambda: [0])
    primary_channel: int = 0
