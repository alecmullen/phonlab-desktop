from dataclasses import dataclass, field


@dataclass
class AudioOpenOptions:
    target_fs: int = 16000
    channel_mode: str = "mono"  # "mono" | "stereo" | "multichannel"
    retained_channels: list[int] = field(default_factory=lambda: [0])
    primary_channel: int = 0
