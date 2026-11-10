from dataclasses import replace

import numpy as np
import pytest
from pytestqt.qtbot import QtBot
from support.view_models import make_spectrogram_view_model

from ui.base.state import State
from ui.spectrogram.spectrogram_plot import SpectrogramPlot
from ui.spectrogram.state.formant_settings import FormantSettingsState
from ui.spectrogram.state.formant_track_state import FormantTrackState
from ui.spectrogram.state.spectrogram_state import SpectrogramState


def make_sgram_state(**overrides: object) -> SpectrogramState:
    defaults = {
        "f": np.array([0.0, 100.0, 200.0]),
        "t_window": np.array([0.0, 1.0, 2.0]),
        "sxx_window": np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]),
        "is_showing": True,
        "is_loading": False,
        "low_sxx": 0.0,
        "high_sxx": 9.0,
        "gray_cutoff": 0.5,
    }
    defaults.update(overrides)
    return SpectrogramState(**defaults)


def test_init_does_not_show_center_label_while_loading(qtbot: QtBot):
    view_model = make_spectrogram_view_model()
    plot = SpectrogramPlot(view_model)

    assert plot.center_label.isVisible() is False


def test_on_state_change_plots_spectrogram_for_spectrogram_state(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = make_spectrogram_view_model()
    plot = SpectrogramPlot(view_model)

    calls = []
    monkeypatch.setattr(plot, "plot_spectrogram", lambda state: calls.append(state))

    state = make_sgram_state()
    plot.on_state_change(state)

    assert calls == [state]


def test_on_state_change_ignores_other_state_types(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = make_spectrogram_view_model()
    plot = SpectrogramPlot(view_model)

    calls = []
    monkeypatch.setattr(plot, "plot_spectrogram", lambda state: calls.append(state))

    plot.on_state_change(State())

    assert calls == []


def test_plot_spectrogram_shows_too_big_label_when_not_showing_and_not_loading(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = make_spectrogram_view_model()
    plot = SpectrogramPlot(view_model)

    calls = []
    monkeypatch.setattr(plot, "display_window_too_big", lambda: calls.append(True))

    plot.plot_spectrogram(make_sgram_state(is_showing=False, is_loading=False))

    assert calls == [True]


def test_plot_spectrogram_populates_when_showing(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = make_spectrogram_view_model()
    plot = SpectrogramPlot(view_model)

    calls = []
    monkeypatch.setattr(plot, "populate_spectrogram", lambda state: calls.append(state))

    state = make_sgram_state(is_showing=True)
    plot.plot_spectrogram(state)

    assert calls == [state]


def test_plot_spectrogram_does_nothing_while_loading_and_not_showing(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = make_spectrogram_view_model()
    plot = SpectrogramPlot(view_model)

    populate_calls = []
    too_big_calls = []
    monkeypatch.setattr(
        plot, "populate_spectrogram", lambda state: populate_calls.append(state)
    )
    monkeypatch.setattr(
        plot, "display_window_too_big", lambda: too_big_calls.append(True)
    )

    plot.plot_spectrogram(make_sgram_state(is_showing=False, is_loading=True))

    assert populate_calls == []
    assert too_big_calls == []


def test_populate_spectrogram_hides_center_label_and_sets_image(qtbot: QtBot):
    view_model = make_spectrogram_view_model()
    plot = SpectrogramPlot(view_model)
    plot.center_label.setVisible(True)

    sgram = make_sgram_state()

    result = plot.populate_spectrogram(sgram)

    assert result is True
    assert plot.center_label.isVisible() is False
    np.testing.assert_array_equal(plot.spec_img.image, sgram.sxx_window.T)


def test_populate_spectrogram_sets_gray_scale_levels(qtbot: QtBot):
    view_model = make_spectrogram_view_model()
    plot = SpectrogramPlot(view_model)

    sgram = make_sgram_state(low_sxx=0.0, high_sxx=10.0, gray_cutoff=0.5)

    plot.populate_spectrogram(sgram)

    vmin, vmax = plot.spec_img.levels
    assert vmin == pytest.approx(5.0)
    assert vmax == pytest.approx(np.max(sgram.sxx_window))


def test_populate_spectrogram_positions_image_by_time_and_frequency_range(
    qtbot: QtBot,
):
    view_model = make_spectrogram_view_model()
    plot = SpectrogramPlot(view_model)

    sgram = make_sgram_state(
        f=np.array([10.0, 20.0, 30.0]), t_window=np.array([1.0, 2.0, 3.0])
    )

    plot.populate_spectrogram(sgram)

    rect = plot.spec_img.mapRectToParent(plot.spec_img.boundingRect())
    assert rect.x() == pytest.approx(1.0)
    assert rect.y() == pytest.approx(10.0)
    assert rect.width() == pytest.approx(2.0)
    assert rect.height() == pytest.approx(20.0)


def test_populate_spectrogram_sets_view_y_range(qtbot: QtBot):
    view_model = make_spectrogram_view_model()
    plot = SpectrogramPlot(view_model)

    sgram = make_sgram_state(f=np.array([5.0, 15.0, 25.0]))

    plot.populate_spectrogram(sgram)

    assert plot.getViewBox().state["limits"]["yLimits"] == [0, 25.0]


def test_display_window_too_big_clears_image_and_shows_label(qtbot: QtBot):
    view_model = make_spectrogram_view_model()
    plot = SpectrogramPlot(view_model)
    plot.populate_spectrogram(make_sgram_state())

    plot.display_window_too_big()

    assert plot.center_label.isVisible() is True
    assert plot.spec_img.image is None


def test_adjust_gray_scale_scales_trackpad_delta_and_forwards_to_view_model(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = make_spectrogram_view_model()
    plot = SpectrogramPlot(view_model)

    calls = []
    monkeypatch.setattr(
        view_model, "adjust_gray_scale", lambda adjustment: calls.append(adjustment)
    )

    plot.adjust_gray_scale(is_trackpad=True, delta=10.0)

    assert calls == [pytest.approx(0.005)]


def test_adjust_gray_scale_scales_wheel_delta_and_forwards_to_view_model(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = make_spectrogram_view_model()
    plot = SpectrogramPlot(view_model)

    calls = []
    monkeypatch.setattr(
        view_model, "adjust_gray_scale", lambda adjustment: calls.append(adjustment)
    )

    plot.adjust_gray_scale(is_trackpad=False, delta=10.0)

    assert calls == [pytest.approx(0.1)]


def test_open_settings_dialog_updates_view_model_when_accepted(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = make_spectrogram_view_model()
    plot = SpectrogramPlot(view_model)

    new_settings = replace(view_model.spectrogram_settings, fs=32000)
    monkeypatch.setattr(
        "ui.spectrogram.spectrogram_plot.SpectrogramSettingsDialog.open_spectrogram_settings",
        staticmethod(lambda settings: new_settings),
    )
    calls = []
    monkeypatch.setattr(
        view_model, "update_settings", lambda settings: calls.append(settings)
    )

    plot.open_settings_dialog()

    assert calls == [new_settings]


def test_open_settings_dialog_does_nothing_when_cancelled(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = make_spectrogram_view_model()
    plot = SpectrogramPlot(view_model)

    monkeypatch.setattr(
        "ui.spectrogram.spectrogram_plot.SpectrogramSettingsDialog.open_spectrogram_settings",
        staticmethod(lambda settings: None),
    )
    calls = []
    monkeypatch.setattr(
        view_model, "update_settings", lambda settings: calls.append(settings)
    )

    plot.open_settings_dialog()

    assert calls == []


def test_plot_formants_draws_finite_points_only(qtbot: QtBot):
    plot = SpectrogramPlot(make_spectrogram_view_model())

    plot.plot_formants(
        FormantTrackState(
            sec=np.array([1.0, 2.0]),
            formants=np.array([[1.0, 2.0, 3.0, 4.0], [5.0, np.nan, 7.0, 8.0]]),
        )
    )

    x, y = plot.formant_dots.getData()
    np.testing.assert_array_equal(x, [1.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0])
    np.testing.assert_array_equal(y, [1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 8.0])


def test_on_state_change_plots_formants_for_formant_track_state(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    plot = SpectrogramPlot(make_spectrogram_view_model())
    calls = []
    monkeypatch.setattr(plot, "plot_formants", lambda state: calls.append(state))

    state = FormantTrackState()
    plot.on_state_change(state)

    assert calls == [state]


def test_track_formants_action_is_enabled_only_when_spectrogram_shows(qtbot: QtBot):
    plot = SpectrogramPlot(make_spectrogram_view_model())
    assert plot.track_formants_action.isEnabled() is False

    plot.plot_spectrogram(make_sgram_state())
    assert plot.track_formants_action.isEnabled() is True

    plot.plot_spectrogram(make_sgram_state(is_showing=False, is_loading=False))
    assert plot.track_formants_action.isEnabled() is False


def test_open_formant_dialog_tracks_formants_when_accepted(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = make_spectrogram_view_model()
    plot = SpectrogramPlot(view_model)
    new_settings = FormantSettingsState(0.5, 60, 500, 2)
    monkeypatch.setattr(
        "ui.spectrogram.spectrogram_plot.FormantSettingsDialog.open_formant_settings",
        staticmethod(lambda settings: new_settings),
    )
    calls = []
    monkeypatch.setattr(
        view_model, "track_formants", lambda settings: calls.append(settings)
    )

    plot.open_formant_dialog()

    assert calls == [new_settings]


def test_open_formant_dialog_does_nothing_when_cancelled(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    view_model = make_spectrogram_view_model()
    plot = SpectrogramPlot(view_model)
    monkeypatch.setattr(
        "ui.spectrogram.spectrogram_plot.FormantSettingsDialog.open_formant_settings",
        staticmethod(lambda settings: None),
    )
    calls = []
    monkeypatch.setattr(
        view_model, "track_formants", lambda settings: calls.append(settings)
    )

    plot.open_formant_dialog()

    assert calls == []
