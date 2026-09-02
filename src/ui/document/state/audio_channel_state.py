from dataclasses import dataclass

import numpy as np

from core.load_audio.entity.audio_signal import AudioSignal


@dataclass(frozen=True)
class AudioChannelState:
    x: np.ndarray
    fs: int

def to_audio_channel_state(audio_signal: AudioSignal) -> AudioChannelState:
    return AudioChannelState(audio_signal.x, audio_signal.fs)

def to_audio_signal(audio_channel_state: AudioChannelState) -> AudioSignal:
    return AudioSignal(audio_channel_state.x, audio_channel_state.fs)
