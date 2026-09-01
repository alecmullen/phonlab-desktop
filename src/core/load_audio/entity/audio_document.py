from dataclasses import dataclass, field

import numpy as np

from core.load_audio.entity.audio_signal import AudioSignal


@dataclass(frozen=True)
class AudioDocument:
    channels: dict[int, AudioSignal] = field(default_factory = dict)
    primary_channel: int = 0
    channel_mode: str = ""
    is_preview: bool = False
    original_channels: list[np.ndarray] | None = None
    original_fs: int | None = None
