from dataclasses import dataclass, field

import numpy as np

from ui.document.state.audio_channel_state import AudioChannelState


@dataclass
class AudioWaveState:
    x: np.ndarray = field(default_factory=lambda: np.zeros(0))
    fs: int = 0
    min_x: float = 0.0
    max_x: float = 0.0
    t: np.ndarray = field(default_factory=lambda: np.zeros(0))
    max_t: float = 0.0


def to_audio_wave_state(channel: AudioChannelState, start, end):
    min_x = float(np.min(channel.x))
    max_x = float(np.max(channel.x))
    max_t = (len(channel.x) - 1) / channel.fs

    x = channel.x[start:end]
    t = channel.t[start:end]

    return AudioWaveState(x, channel.fs, min_x, max_x, t, max_t)
