from dataclasses import dataclass, field

import numpy as np

from core.entity.audio_signal import AudioSignal


@dataclass
class AudioSignalState:
    x: np.ndarray = field(default_factory=lambda: np.zeros(0))
    fs: int = 0
    t: np.ndarray = field(default_factory=lambda: np.zeros(0))


def to_audio_signal_state(audio_signal: AudioSignal) -> AudioSignalState:
    x, fs = audio_signal.x, audio_signal.fs
    t = np.arange(len(x)) / fs

    return AudioSignalState(x, fs, t)
