from dataclasses import dataclass, field

import numpy as np

from core.load_audio.entity.audio_signal import AudioSignal
from ui.base.state import State


@dataclass(frozen=True)
class AudioChannelState(State):
    x: np.ndarray = field(default_factory=lambda: np.array([]))
    fs: int = 0
    t: np.ndarray = field(default_factory=lambda: np.array([]))


def to_audio_state(channels: dict[int, AudioSignal]) -> dict[int, AudioChannelState]:
    channel_states = {}
    for idx, channel in channels.items():
        channel_states[idx] = to_audio_channel_state(channel)
    return channel_states


def to_audio_channel_state(audio_signal: AudioSignal) -> AudioChannelState:
    x, fs = audio_signal.x, audio_signal.fs
    return AudioChannelState(x, fs, np.arange(len(x)) / fs)


def to_audio_signal(audio_channel_state: AudioChannelState) -> AudioSignal:
    return AudioSignal(audio_channel_state.x, audio_channel_state.fs)
