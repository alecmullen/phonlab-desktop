from pytestqt.qtbot import QtBot

from ui.waveform.audio_wave_view_model import AudioWaveViewModel
from ui.waveform.state.audio_wave_range_state import AudioWaveScaleState
from ui.waveform.state.audio_wave_state import AudioWaveState
from ui.waveform.state.channel_active_state import ChannelActiveState
from ui.waveform.state.delete_channel_state import DeleteChannelState
from ui.waveform.state.toggle_active_channel_state import ToggleChannelActiveState


def test_default_state_has_unit_scale(qtbot: QtBot):
    view_model = AudioWaveViewModel()

    assert view_model.audio_wave_scale_state == AudioWaveScaleState(1.0, 1.0)


def test_update_wave_y_range_increases_scale_on_negative_delta(qtbot: QtBot):
    view_model = AudioWaveViewModel()

    view_model.update_wave_y_range(-1.0)

    assert view_model.audio_wave_scale_state.y_scale == 1.05


def test_update_wave_y_range_decreases_scale_on_positive_delta(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    view_model.audio_wave_scale_state = AudioWaveScaleState(y_scale=2.0)

    view_model.update_wave_y_range(1.0)

    assert view_model.audio_wave_scale_state.y_scale == 1.9


def test_update_wave_y_range_clamps_to_lower_bound(qtbot: QtBot):
    view_model = AudioWaveViewModel()

    view_model.update_wave_y_range(1.0)

    assert view_model.audio_wave_scale_state.y_scale == 1.0


def test_update_wave_y_range_clamps_to_upper_bound(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    view_model.audio_wave_scale_state = AudioWaveScaleState(y_scale=9.9)

    view_model.update_wave_y_range(-1.0)

    assert view_model.audio_wave_scale_state.y_scale == 10.0


def test_update_wave_y_range_computes_scaled_max_from_signal_extrema(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    view_model.audio_wave_state = AudioWaveState(min_x=-5.0, max_x=2.0)

    view_model.update_wave_y_range(-1.0)

    assert view_model.audio_wave_scale_state.scaled_y_max == 5.0 / 1.05


def test_update_wave_y_range_emits_new_scale_state(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    received = []
    view_model.subscribe(received.append)

    view_model.update_wave_y_range(-1.0)

    assert received == [view_model.audio_wave_scale_state]


def test_set_wave_state_replaces_state_and_emits(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    new_state = AudioWaveState(min_x=-1.0, max_x=1.0)
    received = []
    view_model.subscribe(received.append)

    view_model.set_wave_state(new_state)

    assert view_model.audio_wave_state is new_state
    assert len(received) == 1
    assert received[0] is new_state


def test_channel_is_active_by_default(qtbot: QtBot):
    assert AudioWaveViewModel().channel_active_state == ChannelActiveState(True)


def test_set_active_stores_and_emits_state(qtbot: QtBot):
    view_model = AudioWaveViewModel()

    with qtbot.waitSignal(view_model.state_changed) as blocker:
        view_model.set_active(False)

    assert view_model.channel_active_state == ChannelActiveState(False)
    assert blocker.args == [ChannelActiveState(False)]


def test_toggle_active_emits_request_without_changing_state(qtbot: QtBot):
    view_model = AudioWaveViewModel()

    with qtbot.waitSignal(view_model.state_changed) as blocker:
        view_model.toggle_active(False)

    assert blocker.args == [ToggleChannelActiveState(False)]
    assert view_model.channel_active_state == ChannelActiveState(True)


def test_delete_channel_emits_delete_state(qtbot: QtBot):
    view_model = AudioWaveViewModel()

    with qtbot.waitSignal(view_model.state_changed) as blocker:
        view_model.delete_channel()

    assert isinstance(blocker.args[0], DeleteChannelState)
