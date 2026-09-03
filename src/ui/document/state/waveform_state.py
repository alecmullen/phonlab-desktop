from dataclasses import dataclass, field

import numpy as np

from ui.document.state.audio_channel_state import AudioChannelState


@dataclass
class WaveformState:
    x: np.ndarray = field(default_factory=lambda: np.zeros(0))
    fs: int = 0
    min_x: float = 0.0
    max_x: float = 0.0
    t: np.ndarray = field(default_factory=lambda: np.zeros(0))


def to_waveform_state(audio_channel_state: AudioChannelState) -> WaveformState:
    x, fs = audio_channel_state.x, audio_channel_state.fs
    min_x = float(np.min(x))
    max_x = float(np.max(x))
    t = np.arange(len(x)) / fs

    return WaveformState(x, fs, min_x, max_x,  t)
