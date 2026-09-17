import numpy as np

from core.load_audio.entity.audio_signal import AudioSignal
from ui.document.state.audio_channel_state import (
    AudioChannelState,
    to_audio_channel_state,
    to_audio_signal,
    to_audio_signals,
    to_audio_state,
)


def test_post_init_computes_time_vector_from_length_and_fs():
    state = AudioChannelState(np.array([1.0, 2.0, 3.0, 4.0]), fs=2)

    np.testing.assert_array_equal(state.t, [0.0, 0.5, 1.0, 1.5])


def test_default_state_has_empty_time_vector():
    state = AudioChannelState()

    assert state.x.size == 0
    assert state.fs == 0
    assert state.t.size == 0


def test_to_audio_channel_state_converts_signal_and_computes_time():
    signal = AudioSignal(np.array([1.0, 2.0, 3.0]), fs=10)

    state = to_audio_channel_state(signal)

    np.testing.assert_array_equal(state.x, signal.x)
    assert state.fs == 10
    np.testing.assert_array_equal(state.t, [0.0, 0.1, 0.2])


def test_to_audio_signal_round_trips_channel_state():
    state = AudioChannelState(np.array([1.0, 2.0, 3.0]), fs=10)

    signal = to_audio_signal(state)

    np.testing.assert_array_equal(signal.x, state.x)
    assert signal.fs == 10


def test_to_audio_state_converts_all_channels():
    signals = {
        0: AudioSignal(np.array([1.0, 2.0]), fs=5),
        1: AudioSignal(np.array([3.0, 4.0, 5.0]), fs=8),
    }

    states = to_audio_state(signals)

    assert states.keys() == {0, 1}
    np.testing.assert_array_equal(states[0].x, [1.0, 2.0])
    assert states[0].fs == 5
    np.testing.assert_array_equal(states[1].x, [3.0, 4.0, 5.0])
    assert states[1].fs == 8


def test_to_audio_signals_converts_all_channels():
    states = {
        0: AudioChannelState(np.array([1.0, 2.0]), fs=5),
        1: AudioChannelState(np.array([3.0]), fs=8),
    }

    signals = to_audio_signals(states)

    assert signals.keys() == {0, 1}
    np.testing.assert_array_equal(signals[0].x, [1.0, 2.0])
    assert signals[0].fs == 5
    np.testing.assert_array_equal(signals[1].x, [3.0])
    assert signals[1].fs == 8
