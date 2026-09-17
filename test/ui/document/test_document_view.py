import numpy as np
import pytest
from PyQt6.QtCore import QEvent, QMimeData, QPoint, QPointF, Qt, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent, QWheelEvent
from PyQt6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

import ui.document.document_view_model as dvm_module
from core.load_audio.entity.audio_signal import AudioSignal
from ui.document.component.resample_dialog import ResampleAudioDialog
from ui.document.document_view import DocumentView
from ui.document.document_view_model import DocumentViewModel
from ui.document.state.audio_loaded import AudioLoaded
from ui.document.state.document_window_state import DocumentWindowState
from ui.document.state.load_progress_state import LoadProgressState
from ui.document.state.mark_state import MarkState
from ui.document.state.playback_state import PlaybackState
from ui.document.state.plot_layout_state import PlotLayoutState
from ui.document.state.select_state import SelectState
from ui.document.state.status_message_state import StatusMessageState


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
    view_model.load_from_samples(AudioSignal(np.arange(20000, dtype=np.float64), 1000))
    QApplication.processEvents()
    return view


def widget_pos_for_time(view: DocumentView, t: float) -> QPoint:
    y = view.wave_plot.getViewBox().viewRange()[1][0]
    scene_pos = view.wave_plot.getViewBox().mapViewToScene(QPointF(t, y))
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


# --------------------------- plot layout / audio loading ---------------------------


def test_load_from_samples_builds_wave_plot_and_sets_up_slider(
    loaded_view: DocumentView,
):
    assert loaded_view.wave_plot is not None
    assert loaded_view.first_plot is loaded_view.wave_plot
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
        loaded_view.wave_plot.getViewBox().mapViewToScene(QPointF(2.0, 0))
    )
    loaded_view.on_mouse_moved(
        loaded_view.wave_plot.getViewBox().mapViewToScene(QPointF(4.0, 0))
    )

    assert view_model.select_state.sel_start == pytest.approx(2.0, abs=1e-6)
    assert view_model.select_state.sel_end == pytest.approx(4.0, abs=1e-6)
    assert loaded_view.is_dragging is True

    release = mouse_event(loaded_view, 4.0, QEvent.Type.MouseButtonRelease)
    loaded_view.handle_mouse_release(release)

    assert loaded_view.mouse_pressed is False
    assert loaded_view.is_dragging is False
    assert len(view_model.audio_player.played) == 1


def test_shift_click_sets_mark_at_click_position(loaded_view: DocumentView):
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

    assert view_model.mark_state.is_set is True
    assert view_model.mark_state.position == pytest.approx(4.0, abs=0.01)


def test_double_click_zooms_to_selection(loaded_view: DocumentView):
    view_model = loaded_view.view_model
    view_model.start_selection(1.0)
    view_model.continue_selection(5.0)

    dbl_click = mouse_event(loaded_view, 2.0, QEvent.Type.MouseButtonDblClick)
    loaded_view.handle_double_click(dbl_click)

    assert view_model.document_window_state.start == 1000
    assert view_model.document_window_state.end == 5000


def test_single_click_after_release_plays_visible_window(
    qtbot: QtBot, loaded_view: DocumentView
):
    view_model = loaded_view.view_model
    press = mouse_event(loaded_view, 2.0, QEvent.Type.MouseButtonPress)
    loaded_view.handle_mouse_press(press)
    release = mouse_event(loaded_view, 2.0, QEvent.Type.MouseButtonRelease)
    loaded_view.handle_mouse_release(release)

    assert loaded_view.click_timer is not None
    qtbot.wait(400)

    assert loaded_view.pending_single_click is None
    assert loaded_view.click_timer is None
    assert len(view_model.audio_player.played) == 1


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
    loaded_view.wave_plot.adjust_y_scale = lambda delta: calls.append(delta)
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


# --------------------------- cleanup ---------------------------


def test_cleanup_closes_view_model_threads(view: DocumentView):
    calls = []
    view.view_model.close_threads = lambda: calls.append(True)

    view.cleanup()

    assert calls == [True]
