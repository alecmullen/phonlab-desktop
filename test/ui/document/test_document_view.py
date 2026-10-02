from itertools import pairwise

import numpy as np
import pytest
from PyQt6.QtCore import QEvent, QMimeData, QPoint, QPointF, Qt, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent, QWheelEvent
from PyQt6.QtWidgets import QApplication, QMessageBox
from pytestqt.qtbot import QtBot

import ui.document.document_view_model as dvm_module
from core.load_audio.entity.audio_signal import AudioSignal
from ui.annotation.annotation_plot import AnnotationPlot
from ui.common.document_plot import DocumentPlot
from ui.document.component.delete_channel_dialog import DeleteChannelDialog
from ui.document.component.paste_special_dialog import (
    PasteSpecialChoice,
    PasteSpecialDialog,
)
from ui.document.component.resample_dialog import ResampleAudioDialog
from ui.document.document_view import PLOT_ROW_SPACING, DocumentView
from ui.document.document_view_model import DocumentViewModel
from ui.document.state.audio_channel_state import (
    AudioChannelState,
    AudioState,
    to_audio_state,
)
from ui.document.state.audio_loaded import AudioLoaded
from ui.document.state.document_window_state import DocumentWindowState
from ui.document.state.load_progress_state import LoadProgressState
from ui.document.state.mark_state import MarkState
from ui.document.state.playback_state import PlaybackState
from ui.document.state.plot_layout_state import PlotLayoutState
from ui.document.state.select_state import SelectState
from ui.document.state.status_message_state import StatusMessageState
from ui.spectrogram.spectrogram_plot import SpectrogramPlot


class FakeAudioPlayer:
    def __init__(self):
        self.played: list[tuple[np.ndarray, int, float]] = []

    def stop(self):
        pass

    def play(self, x: np.ndarray, fs: int, start: float):
        self.played.append((x, fs, start))

    class playback_poll:
        @staticmethod
        def connect(slot: object):
            pass


@pytest.fixture
def view_model(monkeypatch: pytest.MonkeyPatch) -> DocumentViewModel:
    monkeypatch.setattr(dvm_module, "AudioPlayer", FakeAudioPlayer)
    vm = DocumentViewModel()
    vm.prep_audio_spectrogram = lambda: None
    return vm


@pytest.fixture
def view(qtbot: QtBot, view_model: DocumentViewModel) -> DocumentView:
    document_view = DocumentView(view_model)
    qtbot.addWidget(document_view)
    document_view.resize(800, 600)
    document_view.show()
    qtbot.waitExposed(document_view)
    return document_view


@pytest.fixture
def loaded_view(view: DocumentView, view_model: DocumentViewModel) -> DocumentView:
    view_model.load_from_samples(
        to_audio_state({0: AudioSignal(np.arange(20000, dtype=np.float64), 1000)})
    )
    QApplication.processEvents()
    return view


@pytest.fixture
def stereo_loaded_view(
    view: DocumentView, view_model: DocumentViewModel
) -> DocumentView:
    view_model.load_from_samples(
        AudioState(
            {
                0: AudioChannelState(np.arange(20000, dtype=np.float64), 1000),
                1: AudioChannelState(np.arange(20000, dtype=np.float64) * -1, 1000),
            }
        )
    )
    QApplication.processEvents()
    return view


def widget_pos_for_time(view: DocumentView, t: float) -> QPoint:
    y = view.document_plots[0].getViewBox().viewRange()[1][0]
    scene_pos = view.document_plots[0].getViewBox().mapViewToScene(QPointF(t, y))
    return view.graphics_widget.mapFromScene(scene_pos)


def mouse_event(
    view: DocumentView,
    t: float,
    event_type: QEvent.Type,
    modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
) -> QMouseEvent:
    pos = QPointF(widget_pos_for_time(view, t))
    return QMouseEvent(
        event_type, pos, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, modifiers
    )


def click_at_scene_pos(
    view: DocumentView, scene_pos: QPointF, event_type: QEvent.Type
) -> QMouseEvent:
    pos = QPointF(view.graphics_widget.mapFromScene(scene_pos))
    return QMouseEvent(
        event_type,
        pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


# --------------------------- plot layout / audio loading ---------------------------


def test_load_from_samples_builds_wave_plot_and_sets_up_slider(
    loaded_view: DocumentView,
):
    assert len(loaded_view.document_plots) > 0
    assert loaded_view.first_plot is loaded_view.document_plots[0]
    assert loaded_view.slider.maximum() == 9999
    assert loaded_view.slider.pageStep() == 10000


def test_toggle_wave_delegates_to_view_model(view: DocumentView):
    calls = []
    view.view_model.toggle_wave = lambda: calls.append(True)

    view.toggle_wave()

    assert calls == [True]


def test_toggle_spectrogram_delegates_to_view_model(view: DocumentView):
    calls = []
    view.view_model.toggle_spectrogram = lambda: calls.append(True)

    view.toggle_spectrogram()

    assert calls == [True]


def test_toggle_annotations_delegates_to_view_model(view: DocumentView):
    calls = []
    view.view_model.toggle_annotations = lambda: calls.append(True)

    view.toggle_annotations()

    assert calls == [True]


# --------------------------- state dispatch ---------------------------


def test_on_state_change_routes_each_state_type_to_its_handler(view: DocumentView):
    calls = []
    view.reset_slider = lambda fs: calls.append(("reset_slider", fs))
    view.update_plot_layout = lambda s: calls.append(("layout", s))
    view.update_selection_box = lambda s: calls.append(("selection", s))
    view.update_document_window = lambda s: calls.append(("window", s))
    view.update_playback_cursor = lambda s: calls.append(("playback", s))
    view.update_load_progress = lambda s: calls.append(("progress", s))
    view.update_mark = lambda s: calls.append(("mark", s))

    view.on_state_change(AudioLoaded(True, 1000))
    view.on_state_change(SelectState())
    view.on_state_change(DocumentWindowState())
    view.on_state_change(StatusMessageState("hello"))
    view.on_state_change(PlaybackState())
    view.on_state_change(LoadProgressState())
    view.on_state_change(PlotLayoutState())
    view.on_state_change(MarkState())

    assert [c[0] for c in calls] == [
        "reset_slider",
        "layout",
        "selection",
        "window",
        "playback",
        "progress",
        "layout",
        "mark",
    ]
    assert view.message_label.text() == "hello"


# --------------------------- slider ---------------------------


def test_reset_slider_sets_minimum_value_and_step(view: DocumentView):
    view.reset_slider(2000)

    assert view.slider.minimum() == 0
    assert view.slider.value() == 0
    assert view.slider.singleStep() == 100


def test_update_slider_page_step_sets_range_from_window(view: DocumentView):
    view.update_slider_page_step(DocumentWindowState(start=100, end=600, max_start=900))

    assert view.slider.pageStep() == 500
    assert view.slider.minimum() == 0
    assert view.slider.maximum() == 900


def test_update_slider_page_step_clamps_value_to_new_maximum(view: DocumentView):
    view.update_slider_page_step(DocumentWindowState(start=0, end=100, max_start=1000))
    view.slider.setValue(1000)

    view.update_slider_page_step(DocumentWindowState(start=0, end=100, max_start=200))

    assert view.slider.value() == 200


# --------------------------- mouse-driven selection ---------------------------


def test_mouse_drag_creates_selection_and_plays_it_on_release(
    loaded_view: DocumentView,
):
    view_model = loaded_view.view_model
    press = mouse_event(loaded_view, 2.0, QEvent.Type.MouseButtonPress)
    loaded_view.handle_mouse_press(press)

    loaded_view.on_mouse_moved(
        loaded_view.document_plots[0].getViewBox().mapViewToScene(QPointF(2.0, 0))
    )
    loaded_view.on_mouse_moved(
        loaded_view.document_plots[0].getViewBox().mapViewToScene(QPointF(4.0, 0))
    )

    assert view_model.select_state.sel_start == pytest.approx(2.0, abs=1e-6)
    assert view_model.select_state.sel_end == pytest.approx(4.0, abs=1e-6)
    assert loaded_view.is_dragging is True

    release = mouse_event(loaded_view, 4.0, QEvent.Type.MouseButtonRelease)
    loaded_view.handle_mouse_release(release)

    assert loaded_view.mouse_pressed is False
    assert loaded_view.is_dragging is False
    assert len(view_model.audio_player.played) == 1


def test_shift_click_plays_visible_audio(loaded_view: DocumentView):
    view_model = loaded_view.view_model
    press = mouse_event(loaded_view, 4.0, QEvent.Type.MouseButtonPress)
    loaded_view.handle_mouse_press(press)

    release = mouse_event(
        loaded_view,
        4.0,
        QEvent.Type.MouseButtonRelease,
        Qt.KeyboardModifier.ShiftModifier,
    )
    loaded_view.handle_mouse_release(release)

    assert loaded_view.pending_single_click is None
    assert loaded_view.click_timer is None
    assert len(view_model.audio_player.played) == 1


def test_double_click_zooms_to_selection(loaded_view: DocumentView):
    view_model = loaded_view.view_model
    view_model.start_selection(1.0)
    view_model.continue_selection(5.0)

    dbl_click = mouse_event(loaded_view, 2.0, QEvent.Type.MouseButtonDblClick)
    loaded_view.handle_double_click(dbl_click)

    assert view_model.document_window_state.start == 1000
    assert view_model.document_window_state.end == 5000


def test_click_after_release_sets_mark_at_click_position(
    qtbot: QtBot, loaded_view: DocumentView
):
    view_model = loaded_view.view_model
    press = mouse_event(loaded_view, 2.0, QEvent.Type.MouseButtonPress)
    loaded_view.handle_mouse_press(press)
    release = mouse_event(
        loaded_view,
        4.0,
        QEvent.Type.MouseButtonRelease,
    )
    loaded_view.handle_mouse_release(release)

    assert loaded_view.click_timer is not None
    qtbot.wait(400)

    assert view_model.mark_state.is_set is True
    assert view_model.mark_state.position == pytest.approx(4.0, abs=0.01)


# --------------------------- scroll handling ---------------------------


def test_handle_plain_scroll_wheel_uses_larger_fraction_than_trackpad(
    view: DocumentView,
):
    calls = []
    view.view_model.move_start_by_fraction = lambda frac: calls.append(frac)

    view.handle_plain_scroll(10, is_trackpad=False)
    view.handle_plain_scroll(10, is_trackpad=True)

    assert calls == [-1.0, -0.02]


def test_handle_shift_scroll_zooms_in_on_positive_scroll(view: DocumentView):
    calls = []
    view.zoom_in = lambda factor=2: calls.append(("in", factor))
    view.zoom_out = lambda factor=2: calls.append(("out", factor))

    view.handle_shift_scroll(1.0)

    assert calls == [("in", 1.05)]


def test_handle_shift_scroll_zooms_out_on_negative_scroll(view: DocumentView):
    calls = []
    view.zoom_in = lambda factor=2: calls.append(("in", factor))
    view.zoom_out = lambda factor=2: calls.append(("out", factor))

    view.handle_shift_scroll(-1.0)

    assert calls == [("out", 1.05)]


def test_handle_control_scroll_adjusts_wave_plot_y_scale(loaded_view: DocumentView):
    calls = []
    loaded_view.document_plots[0].adjust_y_scale = lambda delta: calls.append(delta)
    pos = QPointF(widget_pos_for_time(loaded_view, 2.0))
    event = QWheelEvent(
        pos,
        pos,
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.ControlModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )

    loaded_view.handle_control_scroll(event, scroll_y=1.0, is_trackpad=False)

    assert calls == [1.0]


def test_event_filter_routes_wheel_event_by_live_keyboard_modifiers(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    # handle_scroll reads QApplication.keyboardModifiers() (the live global
    # modifier state), not the wheel event's own modifiers() value.
    monkeypatch.setattr(
        QApplication,
        "keyboardModifiers",
        staticmethod(lambda: Qt.KeyboardModifier.ShiftModifier),
    )
    calls = []
    loaded_view.zoom_in = lambda factor=2: calls.append(factor)

    event = QWheelEvent(
        QPointF(10, 10),
        QPointF(10, 10),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.ShiftModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )

    handled = loaded_view.eventFilter(loaded_view.graphics_widget.viewport(), event)

    assert handled is True
    assert calls == [1.05]


# --------------------------- drag and drop ---------------------------


def test_drag_enter_event_accepts_url_mime_data(view: DocumentView):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile("/tmp/example.TextGrid")])
    event = QDragEnterEvent(
        QPoint(0, 0),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )

    view.dragEnterEvent(event)

    assert event.isAccepted() is True


def test_drag_enter_event_ignores_non_url_mime_data(view: DocumentView):
    mime = QMimeData()
    mime.setText("not a file")
    event = QDragEnterEvent(
        QPoint(0, 0),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )

    view.dragEnterEvent(event)

    assert event.isAccepted() is False


def test_drop_event_loads_textgrid_from_first_url(view: DocumentView):
    calls = []
    view.load_textgrid = lambda path: calls.append(path)
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile("/tmp/example.TextGrid")])
    event = QDropEvent(
        QPointF(0, 0),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )

    view.dropEvent(event)

    assert calls == ["/tmp/example.TextGrid"]


# --------------------------- resample dialog integration ---------------------------


def test_open_resample_dialog_does_nothing_without_loaded_audio(view: DocumentView):
    calls = []
    view.view_model.resample = lambda fs: calls.append(fs)

    view.open_resample_dialog()

    assert calls == []


def test_open_resample_dialog_resamples_when_dialog_accepted(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        ResampleAudioDialog, "get_target_fs", staticmethod(lambda fs: 32000)
    )
    calls = []
    loaded_view.view_model.resample = lambda fs: calls.append(fs)

    loaded_view.open_resample_dialog()

    assert calls == [32000]


def test_open_resample_dialog_does_not_resample_when_dialog_cancelled(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        ResampleAudioDialog, "get_target_fs", staticmethod(lambda fs: None)
    )
    calls = []
    loaded_view.view_model.resample = lambda fs: calls.append(fs)

    loaded_view.open_resample_dialog()

    assert calls == []


# --------------------------- delete channel button ---------------------------


def test_delete_button_absent_for_mono(loaded_view: DocumentView):
    assert loaded_view.document_plots[0].delete_button_proxy is None


def test_delete_button_present_for_stereo(stereo_loaded_view: DocumentView):
    assert stereo_loaded_view.document_plots[0].delete_button_proxy is not None
    assert stereo_loaded_view.document_plots[1].delete_button_proxy is not None


def test_delete_button_click_deletes_correct_channel(
    stereo_loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        DeleteChannelDialog, "confirm", staticmethod(lambda parent: True)
    )
    scene_pos = (
        stereo_loaded_view.document_plots[1]
        .delete_button_proxy.sceneBoundingRect()
        .center()
    )
    press = click_at_scene_pos(
        stereo_loaded_view, scene_pos, QEvent.Type.MouseButtonPress
    )

    stereo_loaded_view.handle_mouse_press(press)

    assert stereo_loaded_view.view_model.stereo_channels() is None
    np.testing.assert_array_equal(
        stereo_loaded_view.view_model.primary_channel().x,
        np.arange(20000, dtype=np.float64),
    )


def test_delete_button_click_does_not_set_mouse_pressed(
    stereo_loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        DeleteChannelDialog, "confirm", staticmethod(lambda parent: True)
    )
    scene_pos = (
        stereo_loaded_view.document_plots[1]
        .delete_button_proxy.sceneBoundingRect()
        .center()
    )
    press = click_at_scene_pos(
        stereo_loaded_view, scene_pos, QEvent.Type.MouseButtonPress
    )

    stereo_loaded_view.handle_mouse_press(press)

    assert stereo_loaded_view.mouse_pressed is False


def test_delete_button_click_cancelled_dialog_does_nothing(
    stereo_loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        DeleteChannelDialog, "confirm", staticmethod(lambda parent: False)
    )
    scene_pos = (
        stereo_loaded_view.document_plots[1]
        .delete_button_proxy.sceneBoundingRect()
        .center()
    )
    press = click_at_scene_pos(
        stereo_loaded_view, scene_pos, QEvent.Type.MouseButtonPress
    )

    stereo_loaded_view.handle_mouse_press(press)

    assert stereo_loaded_view.view_model.stereo_channels() is not None


def test_double_click_on_delete_button_does_not_zoom(
    stereo_loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    zoom_calls = []
    stereo_loaded_view.view_model.zoom_if_in_selection = lambda x: zoom_calls.append(x)
    scene_pos = (
        stereo_loaded_view.document_plots[1]
        .delete_button_proxy.sceneBoundingRect()
        .center()
    )
    dbl_click = click_at_scene_pos(
        stereo_loaded_view, scene_pos, QEvent.Type.MouseButtonDblClick
    )

    stereo_loaded_view.handle_double_click(dbl_click)

    assert zoom_calls == []


def test_layout_collapses_to_one_row_after_delete(
    stereo_loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        DeleteChannelDialog, "confirm", staticmethod(lambda parent: True)
    )
    scene_pos = (
        stereo_loaded_view.document_plots[1]
        .delete_button_proxy.sceneBoundingRect()
        .center()
    )
    press = click_at_scene_pos(
        stereo_loaded_view, scene_pos, QEvent.Type.MouseButtonPress
    )

    stereo_loaded_view.handle_mouse_press(press)
    QApplication.processEvents()

    assert len(stereo_loaded_view.document_plots) < 2
    assert len(stereo_loaded_view.document_plots) == 1


# --------------------------- paste special ---------------------------


def test_paste_special_shows_message_when_document_already_stereo(
    stereo_loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    info_calls = []
    monkeypatch.setattr(
        QMessageBox,
        "information",
        staticmethod(lambda *a, **k: info_calls.append(True)),
    )
    special_calls = []
    stereo_loaded_view.view_model.paste_special_new_channel_with_silence = (
        lambda *a, **k: special_calls.append(True)
    )
    clip = AudioState({0: AudioSignal(np.full(50, 1.0), 1000)})

    stereo_loaded_view.paste_special(clip)

    assert info_calls == [True]
    assert special_calls == []


def test_paste_special_shows_message_when_clip_is_stereo(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    info_calls = []
    monkeypatch.setattr(
        QMessageBox,
        "information",
        staticmethod(lambda *a, **k: info_calls.append(True)),
    )
    special_calls = []
    loaded_view.view_model.paste_special_new_channel_with_silence = lambda *a, **k: (
        special_calls.append(True)
    )
    clip = AudioState(
        {
            0: AudioSignal(np.full(50, 1.0), 1000),
            1: AudioSignal(np.full(50, -1.0), 1000),
        }
    )

    loaded_view.paste_special(clip)

    assert info_calls == [True]
    assert special_calls == []


def test_paste_special_shows_message_when_mark_not_set(loaded_view: DocumentView):
    received = []
    loaded_view.view_model.subscribe(received.append)
    clip = AudioState({0: AudioSignal(np.full(50, 1.0), 1000)})

    loaded_view.paste_special(clip)

    assert any(isinstance(s, StatusMessageState) for s in received)


def test_paste_special_forwards_with_silence_choice_to_view_model(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    loaded_view.view_model.set_mark(1.0)
    monkeypatch.setattr(
        PasteSpecialDialog,
        "get_choice",
        staticmethod(
            lambda parent=None: PasteSpecialChoice(
                new_channel_idx=1, insert_silence=True
            )
        ),
    )
    with_silence_calls = []
    without_silence_calls = []
    loaded_view.view_model.paste_special_new_channel_with_silence = (
        lambda new_channel_idx, position, clip: with_silence_calls.append(
            (new_channel_idx, position, clip)
        )
    )
    loaded_view.view_model.paste_special_new_channel_without_silence = lambda *a, **k: (
        without_silence_calls.append(True)
    )
    clip = to_audio_state({0: AudioSignal(np.full(50, 1.0), 1000)})

    loaded_view.paste_special(clip)

    assert with_silence_calls == [(1, 1.0, clip)]
    assert without_silence_calls == []


def test_paste_special_forwards_without_silence_choice_to_view_model(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    loaded_view.view_model.set_mark(1.0)
    monkeypatch.setattr(
        PasteSpecialDialog,
        "get_choice",
        staticmethod(
            lambda parent=None: PasteSpecialChoice(
                new_channel_idx=0, insert_silence=False
            )
        ),
    )
    with_silence_calls = []
    without_silence_calls = []
    loaded_view.view_model.paste_special_new_channel_with_silence = lambda *a, **k: (
        with_silence_calls.append(True)
    )
    loaded_view.view_model.paste_special_new_channel_without_silence = (
        lambda new_channel_idx, position, clip: without_silence_calls.append(
            (new_channel_idx, position, clip)
        )
    )
    clip = AudioState({0: AudioSignal(np.full(50, 1.0), 1000)})

    loaded_view.paste_special(clip)

    assert without_silence_calls == [(0, 1.0, clip)]
    assert with_silence_calls == []


def test_paste_special_does_nothing_when_dialog_cancelled(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    loaded_view.view_model.set_mark(1.0)
    monkeypatch.setattr(
        PasteSpecialDialog,
        "get_choice",
        staticmethod(lambda parent=None: None),
    )
    calls = []
    loaded_view.view_model.paste_special_new_channel_with_silence = lambda *a, **k: (
        calls.append(True)
    )
    loaded_view.view_model.paste_special_new_channel_without_silence = lambda *a, **k: (
        calls.append(True)
    )
    clip = AudioState({0: AudioSignal(np.full(50, 1.0), 1000)})

    loaded_view.paste_special(clip)

    assert calls == []


# --------------------------- cleanup ---------------------------


def test_cleanup_closes_view_model_threads(view: DocumentView):
    calls = []
    view.view_model.close_threads = lambda: calls.append(True)

    view.cleanup()

    assert calls == [True]


# --------------------------- document plots (spectrogram / annotation) ---------------------------


@pytest.fixture
def all_plots_view(loaded_view: DocumentView) -> DocumentView:
    loaded_view.view_model.toggle_spectrogram()
    loaded_view.view_model.toggle_annotations()
    QApplication.processEvents()
    return loaded_view


def plot_of(view: DocumentView, cls: type) -> DocumentPlot:
    return next(p for p in view.document_plots if isinstance(p, cls))


def scene_center(plot: DocumentPlot) -> QPointF:
    return plot.sceneBoundingRect().center()


def test_update_plot_layout_adds_spectrogram_and_annotation_plots(
    all_plots_view: DocumentView,
):
    types = [type(p) for p in all_plots_view.document_plots]

    assert SpectrogramPlot in types
    assert AnnotationPlot in types
    assert len(all_plots_view.document_plots) == 3


def test_get_document_plot_at_returns_plot_under_position(
    all_plots_view: DocumentView,
):
    for plot in all_plots_view.document_plots:
        assert all_plots_view._get_document_plot_at(scene_center(plot)) is plot


def test_get_document_plot_at_returns_none_outside_plots(loaded_view: DocumentView):
    assert loaded_view._get_document_plot_at(QPointF(-1000, -1000)) is None


def test_on_mouse_moved_shows_time_status_over_wave_plot(loaded_view: DocumentView):
    loaded_view.on_mouse_moved(scene_center(loaded_view.document_plots[0]))

    assert loaded_view.message_label.text().startswith("Cursor time:")
    assert "frequency" not in loaded_view.message_label.text()


def test_on_mouse_moved_shows_frequency_status_over_spectrogram(
    all_plots_view: DocumentView,
):
    plot = plot_of(all_plots_view, SpectrogramPlot)

    all_plots_view.on_mouse_moved(scene_center(plot))

    assert "frequency" in all_plots_view.message_label.text()


def test_on_mouse_moved_outside_plots_keeps_message(loaded_view: DocumentView):
    loaded_view.message_label.setText("unchanged")

    loaded_view.on_mouse_moved(QPointF(-1000, -1000))

    assert loaded_view.message_label.text() == "unchanged"


def test_on_mouse_moved_while_pressed_starts_then_continues_selection(
    loaded_view: DocumentView,
):
    loaded_view.mouse_pressed = True
    plot = loaded_view.document_plots[0]

    loaded_view.on_mouse_moved(scene_center(plot))
    assert loaded_view.is_dragging is True
    assert loaded_view.view_model.select_state.is_selected is True

    loaded_view.on_mouse_moved(scene_center(plot) + QPointF(20, 0))
    assert loaded_view.view_model.select_state.sel_end > (
        loaded_view.view_model.select_state.sel_start
    )


def test_mouse_press_on_annotation_plot_handled_does_not_start_drag(
    all_plots_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    plot = plot_of(all_plots_view, AnnotationPlot)
    monkeypatch.setattr(plot, "handle_mouse_press", lambda event: True)
    event = click_at_scene_pos(
        all_plots_view, scene_center(plot), QEvent.Type.MouseButtonPress
    )

    all_plots_view.handle_mouse_press(event)

    assert all_plots_view.mouse_pressed is False


def test_mouse_press_on_annotation_plot_unhandled_starts_drag(
    all_plots_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    plot = plot_of(all_plots_view, AnnotationPlot)
    monkeypatch.setattr(plot, "handle_mouse_press", lambda event: False)
    event = click_at_scene_pos(
        all_plots_view, scene_center(plot), QEvent.Type.MouseButtonPress
    )

    all_plots_view.handle_mouse_press(event)

    assert all_plots_view.mouse_pressed is True


def test_mouse_press_outside_plots_does_not_start_drag(loaded_view: DocumentView):
    event = click_at_scene_pos(
        loaded_view, QPointF(-1000, -1000), QEvent.Type.MouseButtonPress
    )

    loaded_view.handle_mouse_press(event)

    assert loaded_view.mouse_pressed is False


def test_mouse_release_without_press_forwards_to_annotation_plots(
    all_plots_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    plot = plot_of(all_plots_view, AnnotationPlot)
    calls = []
    monkeypatch.setattr(plot, "handle_mouse_release", lambda e: calls.append(e))
    event = click_at_scene_pos(
        all_plots_view, scene_center(plot), QEvent.Type.MouseButtonRelease
    )

    all_plots_view.handle_mouse_release(event)

    assert calls == [event]


def test_single_click_on_label_selects_label_and_sets_no_mark(
    all_plots_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    plot = plot_of(all_plots_view, AnnotationPlot)
    monkeypatch.setattr(plot, "handle_single_click", lambda pos: True)
    all_plots_view.pending_single_click = scene_center(plot)

    all_plots_view.handle_single_click()

    assert all_plots_view.view_model.mark_state.is_set is False
    assert all_plots_view.pending_single_click is None
    assert all_plots_view.click_timer is None


def test_single_click_on_annotation_plot_without_label_sets_mark(
    all_plots_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    plot = plot_of(all_plots_view, AnnotationPlot)
    monkeypatch.setattr(plot, "handle_single_click", lambda pos: False)
    all_plots_view.pending_single_click = scene_center(plot)

    all_plots_view.handle_single_click()

    assert all_plots_view.view_model.mark_state.is_set is True


def test_single_click_outside_plots_sets_no_mark(loaded_view: DocumentView):
    loaded_view.pending_single_click = QPointF(-1000, -1000)

    loaded_view.handle_single_click()

    assert loaded_view.view_model.mark_state.is_set is False


def test_control_scroll_adjusts_spectrogram_gray_scale(all_plots_view: DocumentView):
    plot = plot_of(all_plots_view, SpectrogramPlot)
    calls = []
    plot.adjust_gray_scale = lambda is_trackpad, delta: calls.append(
        (is_trackpad, delta)
    )
    pos = all_plots_view.graphics_widget.mapFromScene(scene_center(plot))
    pos = QPointF(pos)
    event = QWheelEvent(
        pos,
        pos,
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.ControlModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )

    all_plots_view.handle_control_scroll(event, scroll_y=2.0, is_trackpad=True)

    assert calls == [(True, 2.0)]


def test_set_mark_if_in_plot_sets_mark_inside_plot(loaded_view: DocumentView):
    loaded_view.set_mark_if_in_plot(scene_center(loaded_view.document_plots[0]))

    assert loaded_view.view_model.mark_state.is_set is True


def test_set_mark_if_in_plot_ignores_position_outside_plots(
    loaded_view: DocumentView,
):
    loaded_view.set_mark_if_in_plot(QPointF(-1000, -1000))

    assert loaded_view.view_model.mark_state.is_set is False


def test_play_window_or_selection_plays_selection_when_click_inside_it(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    view_model = loaded_view.view_model
    view_model.start_selection(2.0)
    view_model.continue_selection(6.0)
    calls = []
    monkeypatch.setattr(view_model, "play_selected_audio", lambda: calls.append("sel"))
    monkeypatch.setattr(view_model, "play_visible_audio", lambda: calls.append("vis"))
    plot = loaded_view.document_plots[0]
    inside = plot.getViewBox().mapViewToScene(QPointF(4.0, 0.0))

    loaded_view.play_window_or_selection(inside)

    assert calls == ["sel"]


def test_play_window_or_selection_ignores_click_outside_plots(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    calls = []
    monkeypatch.setattr(
        loaded_view.view_model, "play_visible_audio", lambda: calls.append("vis")
    )

    loaded_view.play_window_or_selection(QPointF(-1000, -1000))

    assert calls == []


def test_update_playback_cursor_moves_cursor_on_all_plots(
    all_plots_view: DocumentView,
):
    all_plots_view.update_playback_cursor(PlaybackState(True, 3.0))

    assert all(p.cursor_line.value() == 3.0 for p in all_plots_view.document_plots)


def test_update_mark_sets_mark_line_on_all_plots(all_plots_view: DocumentView):
    all_plots_view.update_mark(MarkState(position=2.0, is_set=True))

    assert all(p.mark_line.value() == 2.0 for p in all_plots_view.document_plots)


def test_update_load_progress_toggles_progress_bar(view: DocumentView):
    view.update_load_progress(LoadProgressState(True))
    assert view.progress_bar.isVisible()

    view.update_load_progress(LoadProgressState(False))
    assert not view.progress_bar.isVisible()


# --------------------------- delegation / event filter ---------------------------


@pytest.mark.parametrize(
    ("view_method", "vm_method", "args"),
    [
        ("go_back", "go_back", ()),
        ("advance", "advance", ()),
        ("zoom_out", "zoom_out", (3,)),
        ("zoom_in", "zoom_in", (3,)),
        ("show_all", "show_all", ()),
        ("recenter_on_selection", "center_on_selection", ()),
        ("undo", "undo", ()),
        ("redo", "redo", ()),
    ],
)
def test_view_methods_delegate_to_view_model(
    view: DocumentView,
    monkeypatch: pytest.MonkeyPatch,
    view_method: str,
    vm_method: str,
    args: tuple,
):
    calls = []
    monkeypatch.setattr(
        view.view_model, vm_method, lambda *a: calls.append(a), raising=True
    )

    getattr(view, view_method)(*args)

    assert calls == [args]


def test_event_filter_routes_mouse_events_to_handlers(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    calls = []
    monkeypatch.setattr(
        loaded_view, "handle_double_click", lambda e: calls.append("double")
    )
    monkeypatch.setattr(
        loaded_view, "handle_mouse_press", lambda e: calls.append("press")
    )
    monkeypatch.setattr(
        loaded_view, "handle_mouse_release", lambda e: calls.append("release")
    )
    viewport = loaded_view.graphics_widget.viewport()

    for event_type in (
        QEvent.Type.MouseButtonDblClick,
        QEvent.Type.MouseButtonPress,
        QEvent.Type.MouseButtonRelease,
    ):
        event = mouse_event(loaded_view, 2.0, event_type)
        assert loaded_view.eventFilter(viewport, event) is True

    assert calls == ["double", "press", "release"]


def test_event_filter_right_press_records_context_position(
    loaded_view: DocumentView,
):
    viewport = loaded_view.graphics_widget.viewport()
    pos = QPointF(widget_pos_for_time(loaded_view, 2.0))
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        pos,
        Qt.MouseButton.RightButton,
        Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier,
    )

    loaded_view.eventFilter(viewport, event)

    assert loaded_view.context_pos is not None


def test_plot_rows_are_sized_one_two_one(all_plots_view: DocumentView):
    all_plots_view.resize(900, 700)
    QApplication.processEvents()
    wave, spec, annot = [p.getViewBox().height() for p in all_plots_view.document_plots]

    assert spec == pytest.approx(2 * wave, rel=0.03)
    assert annot == pytest.approx(wave, rel=0.03)


def test_apply_row_heights_without_plots_does_nothing(view: DocumentView):
    view.row_weights = []

    view.apply_row_heights()


def test_plot_rows_have_spacing_between_them(all_plots_view: DocumentView):
    all_plots_view.resize(900, 700)
    QApplication.processEvents()
    rects = [p.sceneBoundingRect() for p in all_plots_view.document_plots]

    for upper, lower in pairwise(rects):
        assert lower.top() - upper.bottom() == pytest.approx(PLOT_ROW_SPACING, abs=1)
