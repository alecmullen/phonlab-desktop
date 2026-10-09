import numpy as np
import pyqtgraph as pg
import pytest
from pytestqt.qtbot import QtBot

from ui.base.state import State
from ui.waveform.audio_wave_plot import ACTIVE_PEN, INACTIVE_PEN, AudioWavePlot
from ui.waveform.audio_wave_view_model import AudioWaveViewModel
from ui.waveform.component.delete_channel_dialog import DeleteChannelDialog
from ui.waveform.state.audio_wave_range_state import AudioWaveScaleState
from ui.waveform.state.audio_wave_state import AudioWaveState
from ui.waveform.state.channel_active_state import ChannelActiveState


def make_wave_state(**overrides: object) -> AudioWaveState:
    defaults = {
        "x": np.array([0.0, 1.0, -1.0, 2.0]),
        "fs": 1000,
        "min_x": -1.0,
        "max_x": 2.0,
        "t": np.array([0.0, 0.001, 0.002, 0.003]),
        "max_t": 0.003,
    }
    defaults.update(overrides)
    return AudioWaveState(**defaults)


def test_init_without_initial_wave_leaves_plot_uninitialized(qtbot: QtBot):
    view_model = AudioWaveViewModel()

    plot = AudioWavePlot(view_model)

    assert plot.is_initialized is False
    assert plot.wave_curve is None


def test_init_with_initial_wave_plots_and_marks_initialized(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    view_model.audio_wave_state = make_wave_state()

    plot = AudioWavePlot(view_model)

    assert plot.is_initialized is True
    assert plot.wave_curve is not None
    np.testing.assert_array_equal(plot.wave_curve.xData, view_model.audio_wave_state.t)
    np.testing.assert_array_equal(plot.wave_curve.yData, view_model.audio_wave_state.x)


def test_on_state_change_plots_wave_on_first_audio_wave_state(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model)
    assert plot.is_initialized is False

    calls = []
    monkeypatch.setattr(plot, "plot_wave", lambda state: calls.append(state))

    state = make_wave_state()
    plot.on_state_change(state)

    assert calls == [state]
    assert plot.is_initialized is True


def test_on_state_change_updates_wave_on_subsequent_audio_wave_state(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = AudioWaveViewModel()
    view_model.audio_wave_state = make_wave_state()
    plot = AudioWavePlot(view_model)
    assert plot.is_initialized is True

    calls = []
    monkeypatch.setattr(plot, "update_wave", lambda state: calls.append(state))

    state = make_wave_state(x=np.array([5.0, 6.0, 7.0, 8.0]))
    plot.on_state_change(state)

    assert calls == [state]


def test_on_state_change_updates_y_range_for_scale_state(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model)

    calls = []
    monkeypatch.setattr(
        plot, "update_y_range", lambda scaled_y_max: calls.append(scaled_y_max)
    )

    plot.on_state_change(AudioWaveScaleState(y_scale=2.0, scaled_y_max=4.5))

    assert calls == [4.5]


def test_on_state_change_ignores_other_state_types(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model)

    plot_calls = []
    update_calls = []
    y_range_calls = []
    monkeypatch.setattr(plot, "plot_wave", lambda state: plot_calls.append(state))
    monkeypatch.setattr(plot, "update_wave", lambda state: update_calls.append(state))
    monkeypatch.setattr(
        plot, "update_y_range", lambda scaled_y_max: y_range_calls.append(scaled_y_max)
    )

    plot.on_state_change(State())

    assert plot_calls == []
    assert update_calls == []
    assert y_range_calls == []


def test_plot_wave_sets_symmetric_y_limits_from_extrema(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model)

    plot.plot_wave(make_wave_state(min_x=-3.0, max_x=2.0))

    assert plot.getViewBox().state["limits"]["yLimits"] == [-3.0, 3.0]


def test_plot_wave_sets_x_limits_from_max_t(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model)

    plot.plot_wave(make_wave_state(max_t=5.0))

    assert plot.getViewBox().state["limits"]["xLimits"] == [0, 5.0]


def test_plot_wave_creates_curve_with_time_and_amplitude_data(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model)

    state = make_wave_state()
    plot.plot_wave(state)

    np.testing.assert_array_equal(plot.wave_curve.xData, state.t)
    np.testing.assert_array_equal(plot.wave_curve.yData, state.x)


def test_update_wave_replaces_curve_data(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    view_model.audio_wave_state = make_wave_state()
    plot = AudioWavePlot(view_model)

    new_state = make_wave_state(t=np.array([0.0, 0.1]), x=np.array([9.0, -9.0]))
    plot.update_wave(new_state)

    np.testing.assert_array_equal(plot.wave_curve.xData, new_state.t)
    np.testing.assert_array_equal(plot.wave_curve.yData, new_state.x)


def test_update_selection_region_shows_region_for_positive_range(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model)

    plot.update_selection_region(1.0, 2.0)

    assert plot.selection_region.isVisible() is True
    assert list(plot.selection_region.getRegion()) == [1.0, 3.0]


def test_update_selection_region_hides_region_for_zero_or_negative_range(
    qtbot: QtBot,
):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model)
    plot.update_selection_region(1.0, 2.0)

    plot.update_selection_region(1.0, -1.0)

    assert plot.selection_region.isVisible() is False


def test_adjust_y_scale_forwards_delta_to_view_model(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model)

    calls = []
    monkeypatch.setattr(
        view_model, "update_wave_y_range", lambda delta: calls.append(delta)
    )

    plot.adjust_y_scale(-3.5)

    assert calls == [-3.5]


def test_update_y_range_sets_symmetric_view_range(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model)

    plot.update_y_range(4.0)

    assert plot.getViewBox().viewRange()[1] == [-4.0, 4.0]


def test_on_mouse_moved_updates_cursor_when_in_control(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model)

    from PyQt6.QtCore import QPointF

    layout = pg.GraphicsLayoutWidget()
    qtbot.addWidget(layout)
    layout.addItem(plot)
    layout.resize(400, 300)
    layout.show()
    qtbot.waitExposed(layout)

    plot.has_cursor_control = True
    scene_pos = plot.getViewBox().mapViewToScene(QPointF(0.5, 0.0))

    plot.on_mouse_moved(scene_pos)

    assert plot.cursor_line.value() == pytest.approx(0.5)


def test_set_cursor_position_moves_line_and_removes_control(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model)

    plot.set_cursor_position(2.0)

    assert plot.cursor_line.value() == 2.0
    assert plot.has_cursor_control is False


def test_set_mark_position_moves_line_and_sets_visibility(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model)

    assert plot.mark_line.isVisible() is False

    plot.set_mark_position(1.5, True)
    assert plot.mark_line.value() == 1.5
    assert plot.mark_line.isVisible() is True

    plot.set_mark_position(1.5, False)
    assert plot.mark_line.isVisible() is False


def test_clear_resets_wave_curve(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    view_model.audio_wave_state = make_wave_state()
    plot = AudioWavePlot(view_model)
    assert plot.wave_curve is not None

    plot.clear()

    assert plot.wave_curve is None


def test_controls_are_hidden_by_default(qtbot: QtBot):
    plot = AudioWavePlot(AudioWaveViewModel())

    assert plot.active_checkbox is None
    assert plot.delete_button is None


def test_controls_are_created_when_requested(qtbot: QtBot):
    plot = AudioWavePlot(
        AudioWaveViewModel(), show_active_checkbox=True, show_delete_button=True
    )

    assert plot.active_checkbox is not None
    assert plot.delete_button is not None


def test_active_checkbox_starts_checked_and_curve_uses_active_pen(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    view_model.audio_wave_state = make_wave_state()

    plot = AudioWavePlot(view_model, show_active_checkbox=True)

    assert plot.active_checkbox.isChecked() is True
    assert plot.wave_curve.opts["pen"] == ACTIVE_PEN


def test_active_checkbox_reflects_inactive_initial_state(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    view_model.audio_wave_state = make_wave_state()
    view_model.channel_active_state = ChannelActiveState(is_active=False)

    plot = AudioWavePlot(view_model, show_active_checkbox=True)

    assert plot.active_checkbox.isChecked() is False
    assert plot.wave_curve.opts["pen"] == INACTIVE_PEN


def test_toggling_checkbox_forwards_to_view_model(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model, show_active_checkbox=True)
    calls = []
    monkeypatch.setattr(view_model, "toggle_active", lambda a: calls.append(a))

    plot.active_checkbox.setChecked(False)
    plot.active_checkbox.setChecked(True)

    assert calls == [False, True]


def test_channel_active_state_updates_checkbox_and_pen(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    view_model.audio_wave_state = make_wave_state()
    plot = AudioWavePlot(view_model, show_active_checkbox=True)

    plot.on_state_change(ChannelActiveState(is_active=False))

    assert plot.active_checkbox.isChecked() is False
    assert plot.wave_curve.opts["pen"] == INACTIVE_PEN

    plot.on_state_change(ChannelActiveState(is_active=True))

    assert plot.active_checkbox.isChecked() is True
    assert plot.wave_curve.opts["pen"] == ACTIVE_PEN


def test_channel_active_state_without_checkbox_still_updates_pen(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    view_model.audio_wave_state = make_wave_state()
    plot = AudioWavePlot(view_model)

    plot.on_state_change(ChannelActiveState(is_active=False))

    assert plot.wave_curve.opts["pen"] == INACTIVE_PEN


def test_channel_active_state_before_wave_exists_does_not_fail(qtbot: QtBot):
    plot = AudioWavePlot(AudioWaveViewModel(), show_active_checkbox=True)

    plot.on_state_change(ChannelActiveState(is_active=False))

    assert plot.active_checkbox.isChecked() is False


def test_view_model_toggle_active_updates_plot(qtbot: QtBot):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model, show_active_checkbox=True)

    view_model.toggle_active(False)

    assert plot.active_checkbox.isChecked() is False


def test_delete_channel_confirmed_forwards_to_view_model(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model, show_delete_button=True)
    calls = []
    monkeypatch.setattr(view_model, "delete_channel", lambda: calls.append(True))
    monkeypatch.setattr(DeleteChannelDialog, "confirm", lambda parent: True)

    plot.delete_channel()

    assert calls == [True]


def test_delete_channel_cancelled_does_nothing(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model, show_delete_button=True)
    calls = []
    monkeypatch.setattr(view_model, "delete_channel", lambda: calls.append(True))
    monkeypatch.setattr(DeleteChannelDialog, "confirm", lambda parent: False)

    plot.delete_channel()

    assert calls == []


def test_delete_button_click_asks_for_confirmation(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = AudioWaveViewModel()
    plot = AudioWavePlot(view_model, show_delete_button=True)
    asked = []
    monkeypatch.setattr(
        DeleteChannelDialog, "confirm", lambda parent: asked.append(True) or False
    )

    plot.delete_button.click()

    assert asked == [True]
