from dataclasses import dataclass, field

import numpy as np

from core.load_audio.entity.audio_signal import AudioSignal


@dataclass(frozen=True)
class PreppedAudioChannelState:
    x: np.ndarray
    fs: int

@dataclass(frozen=True)
class PreppedAudioState:
    channels: dict[int, PreppedAudioChannelState] = field(default_factory = dict)

def to_prepped_audio_state(audio_signals: dict[int, AudioSignal]) -> PreppedAudioState:
    channels = {
        idx: PreppedAudioChannelState(x=signal.x, fs=signal.fs)
        for idx, signal in audio_signals.items()
    }
    return PreppedAudioState(channels=channels)
