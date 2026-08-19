from dataclasses import dataclass, field

import numpy as np

from ui.document.state.audio_signal_state import AudioSignalState


@dataclass
class AudioWaveState:
    x: np.ndarray = field(default_factory=lambda: np.zeros(0))
    fs: int = 0
    min_x: float = 0.0
    max_x: float = 0.0
    t: np.ndarray = field(default_factory=lambda: np.zeros(0))
    max_t: float = 0.0


def to_audio_wave_state(audio_signal: AudioSignalState, start, end):
    min_x = np.min(audio_signal.x)
    max_x = np.max(audio_signal.x)
    max_t = (len(audio_signal.x) - 1) / audio_signal.fs

    x = audio_signal.x[start:end]
    t = (np.arange(len(x)) + start) / audio_signal.fs

    return AudioWaveState(x, audio_signal.fs, min_x, max_x, t, max_t)
