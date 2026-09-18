import numpy as np

from ui.document.state.audio_channel_state import AudioChannelState
from ui.waveform.state.audio_wave_state import to_audio_wave_state


def test_to_audio_wave_state_slices_x_and_t_to_window():
    channel = AudioChannelState(np.arange(10, dtype=np.float64), fs=10)

    state = to_audio_wave_state(channel, start=2, end=5)

    np.testing.assert_array_equal(state.x, [2.0, 3.0, 4.0])
    np.testing.assert_array_equal(state.t, channel.t[2:5])
    assert state.fs == 10


def test_to_audio_wave_state_computes_min_max_from_full_channel_not_window():
    channel = AudioChannelState(
        np.array([-5.0, 0.0, 1.0, 2.0, 3.0], dtype=np.float64), fs=1
    )

    state = to_audio_wave_state(channel, start=2, end=4)

    assert state.min_x == -5.0
    assert state.max_x == 3.0


def test_to_audio_wave_state_computes_max_t_from_channel_length_and_fs():
    channel = AudioChannelState(np.zeros(101, dtype=np.float64), fs=100)

    state = to_audio_wave_state(channel, start=0, end=10)

    assert state.max_t == 1.0
