from dataclasses import dataclass, field

import numpy as np

from core.load_audio.entity.audio_signal import AudioSignal
from ui.base.state import State


@dataclass(frozen=True)
class AudioChannelState(State):
    x: np.ndarray = field(default_factory=lambda: np.array([]))
    fs: int = 0
    t: np.ndarray = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "t", np.arange(len(self.x)) / self.fs)


@dataclass(frozen=True)
class AudioState(State):
    channels: dict[int, AudioChannelState] = field(default_factory=dict)

    @property
    def is_stereo(self) -> bool:
        return len(self.channels) == 2


def peak_dbfs(x: np.ndarray) -> float:
    """Peak level of `x` in dBFS (full scale = 1.0); -inf for silence."""
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    return 20 * np.log10(peak) if peak > 0 else float("-inf")


def to_audio_state(channels: dict[int, AudioSignal]) -> AudioState:
    channel_states = {}
    for idx, channel in channels.items():
        channel_states[idx] = to_audio_channel_state(channel)
    return AudioState(channel_states)


def to_audio_signals(audio_state: AudioState) -> dict[int, AudioSignal]:
    signals = {}
    for idx, channel in audio_state.channels.items():
        signals[idx] = to_audio_signal(channel)
    return signals


def to_audio_channel_state(audio_signal: AudioSignal) -> AudioChannelState:
    return AudioChannelState(audio_signal.x, audio_signal.fs)


def to_audio_signal(audio_channel_state: AudioChannelState) -> AudioSignal:
    return AudioSignal(audio_channel_state.x, audio_channel_state.fs)
