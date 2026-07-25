from dataclasses import dataclass, field

import numpy as np

from core.entity.audio_signal import AudioSignal


@dataclass
class AudioWaveState:
    y: np.ndarray = field(default_factory=lambda: np.zeros(0))
    fs: int = 0
    miny: float = 0.0
    maxy: float = 0.0
    yrange: float = 0.0
    t: np.ndarray = field(default_factory=lambda: np.zeros(0))

def to_audio_wave_state(audio_signal: AudioSignal) -> AudioWaveState:
    y, fs = audio_signal.y, audio_signal.fs
    miny = np.min(y)
    maxy = np.max(y)
    yrange = maxy - miny
    t = np.arange(len(y)) / fs

    return AudioWaveState(y, fs, miny, maxy, yrange, t)
