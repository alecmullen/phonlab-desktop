from dataclasses import dataclass

import numpy as np

from core.load_audio.entity.audio_signal import AudioSignal


@dataclass(frozen=True)
class AudioChannelState:
    x: np.ndarray
    fs: int
    t: np.ndarray


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
