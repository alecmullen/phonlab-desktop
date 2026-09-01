from dataclasses import dataclass, field

import numpy as np

from core.load_audio.entity.audio_signal import AudioSignal


@dataclass
class AudioWaveState:
    x: np.ndarray = field(default_factory=lambda: np.zeros(0))
    fs: int = 0
    min_x: float = 0.0
    max_x: float = 0.0
    x_range: float = 0.0
    t: np.ndarray = field(default_factory=lambda: np.zeros(0))


def to_audio_wave_state(audio_signal: AudioSignal) -> AudioWaveState:
    x, fs = audio_signal.x, audio_signal.fs
    min_x = np.min(x)
    max_x = np.max(x)
    x_range = max_x - min_x
    t = np.arange(len(x)) / fs

    return AudioWaveState(x, fs, min_x, max_x, x_range, t)
