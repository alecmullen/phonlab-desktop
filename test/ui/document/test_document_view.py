from itertools import pairwise

import numpy as np
import pytest
from PyQt6.QtCore import QEvent, QMimeData, QPoint, QPointF, QRectF, Qt, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent, QWheelEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMessageBox
from pytestqt.qtbot import QtBot

from core.load_audio.entity.audio_signal import AudioSignal
from core.transform_audio.entity.filter_spec import FilterType
from core.transform_audio.filter_audio import FilterSpec
from res.constants import DOUBLE_CLICK_INTERVAL_MS
from ui.annotation.annotation_plot import AnnotationPlot
from ui.annotation.component.add_tiers_dialog import AddTiersDialog
from ui.annotation.state.add_tiers_state import AddTiersAction
from ui.annotation.state.save_to_textgrid_state import SaveToTextGridAction
from ui.common.document_plot import DocumentPlot
from ui.document.component.filter_dialog import FilterAudioDialog
from ui.document.component.paste_special_dialog import (
    PasteSpecialChoice,
    PasteSpecialDialog,
)
from ui.document.component.resample_dialog import ResampleAudioDialog
from ui.document.component.save_textgrid_dialog import SaveTextGridDialog
from ui.document.component.scale_dialog import ScaleAudioDialog
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
from ui.waveform.component.delete_channel_dialog import DeleteChannelDialog


@pytest.fixture
def view(qtbot: QtBot, document_view_model: DocumentViewModel) -> DocumentView:
    document_view = DocumentView(document_view_model)
    qtbot.addWidget(document_view)
    document_view.resize(800, 600)
    document_view.show()
    qtbot.waitExposed(document_view)
    return document_view


@pytest.fixture
def loaded_view(
    view: DocumentView, document_view_model: DocumentViewModel
) -> DocumentView:
    document_view_model.load_from_samples(
        to_audio_state({0: AudioSignal(np.arange(20000, dtype=np.float64), 1000)})
    )
    QApplication.processEvents()
    return view


@pytest.fixture
def stereo_loaded_view(
    view: DocumentView, document_view_model: DocumentViewModel
) -> DocumentView:
    document_view_model.load_from_samples(
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
    return scene_pos + view.graphics_widget.pos().toPointF()


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
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(loaded_view, "left_button_is_down", lambda: True)
    document_view_model = loaded_view.view_model
    press = mouse_event(loaded_view, 2.0, QEvent.Type.MouseButtonPress)
    loaded_view.mousePressEvent(press)

    loaded_view.on_mouse_moved(
        loaded_view.document_plots[0].getViewBox().mapViewToScene(QPointF(2.0, 0))
    )
    loaded_view.on_mouse_moved(
        loaded_view.document_plots[0].getViewBox().mapViewToScene(QPointF(4.0, 0))
    )

    assert document_view_model.select_state.sel_start == pytest.approx(2.0, abs=1e-6)
    assert document_view_model.select_state.sel_end == pytest.approx(4.0, abs=1e-6)
    assert loaded_view.is_dragging is True

    release = mouse_event(loaded_view, 4.0, QEvent.Type.MouseButtonRelease)
    loaded_view.mouseReleaseEvent(release)

    assert loaded_view.mouse_pressed is False
    assert loaded_view.is_dragging is False
    assert len(document_view_model.audio_player.played) == 1


def test_shift_click_plays_visible_audio(loaded_view: DocumentView):
    document_view_model = loaded_view.view_model
    press = mouse_event(loaded_view, 4.0, QEvent.Type.MouseButtonPress)
    loaded_view.mousePressEvent(press)

    release = mouse_event(
        loaded_view,
        4.0,
        QEvent.Type.MouseButtonRelease,
        Qt.KeyboardModifier.ShiftModifier,
    )
    loaded_view.mouseReleaseEvent(release)

    assert loaded_view.pending_single_click is None
    assert loaded_view.click_timer is None
    assert len(document_view_model.audio_player.played) == 1


def test_double_click_zooms_to_selection(loaded_view: DocumentView):
    document_view_model = loaded_view.view_model
    document_view_model.start_selection(1.0)
    document_view_model.continue_selection(5.0)

    dbl_click = mouse_event(loaded_view, 2.0, QEvent.Type.MouseButtonDblClick)
    loaded_view.mouseDoubleClickEvent(dbl_click)

    assert document_view_model.document_window_state.start == 1000
    assert document_view_model.document_window_state.end == 5000


def test_shift_double_click_plays_the_selection_again_instead_of_zooming(
    loaded_view: DocumentView,
):
    document_view_model = loaded_view.view_model
    document_view_model.start_selection(1.0)
    document_view_model.continue_selection(5.0)
    window_before = document_view_model.document_window_state

    dbl_click = mouse_event(
        loaded_view,
        2.0,
        QEvent.Type.MouseButtonDblClick,
        Qt.KeyboardModifier.ShiftModifier,
    )
    loaded_view.mouseDoubleClickEvent(dbl_click)

    assert document_view_model.document_window_state == window_before
    assert document_view_model.select_state.is_selected
    assert len(document_view_model.audio_player.played) == 1


def test_a_single_click_waits_as_long_as_the_double_click_interval(
    loaded_view: DocumentView,
):
    loaded_view.mousePressEvent(
        mouse_event(loaded_view, 4.0, QEvent.Type.MouseButtonPress)
    )
    loaded_view.mouseReleaseEvent(
        mouse_event(loaded_view, 4.0, QEvent.Type.MouseButtonRelease)
    )

    assert loaded_view.click_timer is not None
    assert loaded_view.click_timer.interval() == DOUBLE_CLICK_INTERVAL_MS


def test_click_after_release_sets_mark_at_click_position(
    qtbot: QtBot, loaded_view: DocumentView
):
    document_view_model = loaded_view.view_model
    press = mouse_event(loaded_view, 4.0, QEvent.Type.MouseButtonPress)
    loaded_view.mousePressEvent(press)
    release = mouse_event(
        loaded_view,
        4.0,
        QEvent.Type.MouseButtonRelease,
    )
    loaded_view.mouseReleaseEvent(release)

    assert loaded_view.click_timer is not None
    qtbot.wait(400)

    assert document_view_model.mark_state.is_set is True
    assert document_view_model.mark_state.position == pytest.approx(4.0, abs=0.01)


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


def drop_event(path: str) -> QDropEvent:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(path)])
    event = QDropEvent(
        QPointF(0, 0),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    # The event does not own its mime data; keep it alive as long as the event
    event.mime_data = mime  # ty: ignore[unresolved-attribute]
    return event


def stub_drop(
    view: DocumentView,
    monkeypatch: pytest.MonkeyPatch,
    has_annotation: bool,
    *answers: QMessageBox.StandardButton,
) -> tuple[list, list]:
    """Returns the (path, overwrite) load_textgrid calls and the questions asked"""
    calls: list = []
    asked: list = []
    remaining = list(answers)
    view.load_textgrid = lambda path, overwrite=False: calls.append((path, overwrite))
    monkeypatch.setattr(view.view_model, "has_annotation", lambda: has_annotation)

    def question(
        parent: object,
        title: str,
        text: str,
        buttons: QMessageBox.StandardButton,
        *args: object,
    ) -> QMessageBox.StandardButton:
        asked.append((text, buttons))
        return remaining.pop(0)

    monkeypatch.setattr(QMessageBox, "question", staticmethod(question))
    return calls, asked


def test_drop_event_loads_textgrid_from_first_url(
    view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    calls, asked = stub_drop(view, monkeypatch, False)

    view.dropEvent(drop_event("/tmp/example.TextGrid"))

    assert calls == [("/tmp/example.TextGrid", False)]
    assert asked == []


def test_drop_event_overwrites_existing_annotation_when_user_says_yes(
    view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    calls, asked = stub_drop(view, monkeypatch, True, QMessageBox.StandardButton.Yes)

    view.dropEvent(drop_event("/tmp/example.TextGrid"))

    assert calls == [("/tmp/example.TextGrid", True)]
    [(text, buttons)] = asked
    assert (
        text == "Overwrite the existing database with annotation from example.TextGrid?"
    )
    assert buttons == QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No


def test_drop_event_keeps_existing_annotation_when_user_says_no(
    view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    calls, _ = stub_drop(view, monkeypatch, True, QMessageBox.StandardButton.No)

    view.dropEvent(drop_event("/tmp/example.TextGrid"))

    assert calls == []


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
    stereo_loaded_view.document_plots[1].delete_channel()

    assert stereo_loaded_view.view_model.stereo_channels() is None
    np.testing.assert_array_equal(
        stereo_loaded_view.view_model.primary_channel().x,
        np.arange(20000, dtype=np.float64),
    )


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

    stereo_loaded_view.mousePressEvent(press)

    assert stereo_loaded_view.view_model.stereo_channels() is not None


# --------------------------- paste special ---------------------------


def test_paste_special_disables_new_channel_when_document_already_stereo(
    stereo_loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    stereo_loaded_view.view_model.set_mark(1.0)
    availability = []
    monkeypatch.setattr(
        PasteSpecialDialog,
        "get_choice",
        staticmethod(
            lambda parent=None, new_channel_available=True: (
                availability.append(new_channel_available) or None
            )
        ),
    )
    clip = AudioState({0: AudioSignal(np.full(50, 1.0), 1000)})

    stereo_loaded_view.paste_special(clip)

    assert availability == [False]


def test_paste_special_disables_new_channel_when_clip_is_stereo(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    loaded_view.view_model.set_mark(1.0)
    availability = []
    monkeypatch.setattr(
        PasteSpecialDialog,
        "get_choice",
        staticmethod(
            lambda parent=None, new_channel_available=True: (
                availability.append(new_channel_available) or None
            )
        ),
    )
    clip = AudioState(
        {
            0: AudioSignal(np.full(50, 1.0), 1000),
            1: AudioSignal(np.full(50, -1.0), 1000),
        }
    )

    loaded_view.paste_special(clip)

    assert availability == [False]


def test_paste_special_without_new_channel_does_a_plain_reversed_paste(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    loaded_view.view_model.set_mark(1.0)
    monkeypatch.setattr(
        PasteSpecialDialog,
        "get_choice",
        staticmethod(
            lambda parent=None, new_channel_available=True: PasteSpecialChoice(
                new_channel_idx=1,
                insert_silence=True,
                reverse=True,
                new_channel=False,
            )
        ),
    )
    special_calls = []
    loaded_view.view_model.paste_special_new_channel_with_silence = lambda *a, **k: (
        special_calls.append(True)
    )
    pasted = []
    loaded_view.view_model.paste_at = lambda position, clip: pasted.append(
        (position, clip)
    )
    clip = AudioState({0: AudioChannelState(np.array([1.0, 2.0, 3.0]), 1000)})

    loaded_view.paste_special(clip)

    assert special_calls == []
    assert pasted[0][0] == 1.0
    np.testing.assert_array_equal(pasted[0][1].channels[0].x, [3.0, 2.0, 1.0])


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
            lambda parent=None, new_channel_available=True: PasteSpecialChoice(
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
            lambda parent=None, new_channel_available=True: PasteSpecialChoice(
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
        staticmethod(lambda parent=None, new_channel_available=True: None),
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
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(loaded_view, "left_button_is_down", lambda: True)
    loaded_view.mouse_pressed = True
    plot = loaded_view.document_plots[0]

    loaded_view.on_mouse_moved(scene_center(plot))
    assert loaded_view.is_dragging is True
    assert loaded_view.view_model.select_state.is_selected is True

    loaded_view.on_mouse_moved(scene_center(plot) + QPointF(20, 0))
    assert loaded_view.view_model.select_state.sel_end > (
        loaded_view.view_model.select_state.sel_start
    )


def test_mouse_press_on_annotation_plot_unhandled_starts_drag(
    all_plots_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    plot = plot_of(all_plots_view, AnnotationPlot)
    monkeypatch.setattr(plot, "mousePressEvent", lambda event: False)
    event = click_at_scene_pos(
        all_plots_view, scene_center(plot), QEvent.Type.MouseButtonPress
    )

    all_plots_view.mousePressEvent(event)

    assert all_plots_view.mouse_pressed is True


def test_mouse_press_outside_plots_does_not_start_drag(loaded_view: DocumentView):
    event = click_at_scene_pos(
        loaded_view, QPointF(-1000, -1000), QEvent.Type.MouseButtonPress
    )

    loaded_view.mousePressEvent(event)

    assert loaded_view.mouse_pressed is False


def test_shift_click_on_an_annotation_label_plays_that_label_not_the_window(
    all_plots_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    plot = plot_of(all_plots_view, AnnotationPlot)
    shift_clicked = []
    monkeypatch.setattr(
        plot, "handle_shift_click", lambda pos: shift_clicked.append(pos) or True
    )
    window_plays = []
    monkeypatch.setattr(
        all_plots_view, "play_window_or_selection", lambda pos: window_plays.append(pos)
    )

    all_plots_view.play_for_shift_click(scene_center(plot))

    assert len(shift_clicked) == 1
    assert window_plays == []


def test_shift_click_in_the_annotation_plot_away_from_labels_plays_the_window(
    all_plots_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    plot = plot_of(all_plots_view, AnnotationPlot)
    monkeypatch.setattr(plot, "handle_shift_click", lambda pos: False)
    window_plays = []
    monkeypatch.setattr(
        all_plots_view, "play_window_or_selection", lambda pos: window_plays.append(pos)
    )

    all_plots_view.play_for_shift_click(scene_center(plot))

    assert len(window_plays) == 1


def test_shift_click_in_another_plot_plays_the_window_or_selection(
    all_plots_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    plot = plot_of(all_plots_view, SpectrogramPlot)
    window_plays = []
    monkeypatch.setattr(
        all_plots_view, "play_window_or_selection", lambda pos: window_plays.append(pos)
    )

    all_plots_view.play_for_shift_click(scene_center(plot))

    assert len(window_plays) == 1


def test_releasing_a_shift_click_plays_without_setting_a_mark(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    plays = []
    monkeypatch.setattr(loaded_view, "play_for_shift_click", plays.append)
    loaded_view.mousePressEvent(
        mouse_event(loaded_view, 4.0, QEvent.Type.MouseButtonPress)
    )

    loaded_view.mouseReleaseEvent(
        mouse_event(
            loaded_view,
            4.0,
            QEvent.Type.MouseButtonRelease,
            Qt.KeyboardModifier.ShiftModifier,
        )
    )

    assert len(plays) == 1
    assert loaded_view.click_timer is None
    assert loaded_view.view_model.mark_state.is_set is False


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
    document_view_model = loaded_view.view_model
    document_view_model.start_selection(2.0)
    document_view_model.continue_selection(6.0)
    calls = []
    monkeypatch.setattr(
        document_view_model, "play_selected_audio", lambda: calls.append("sel")
    )
    monkeypatch.setattr(
        document_view_model, "play_visible_audio", lambda: calls.append("vis")
    )
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
        ("toggle_wave", "toggle_wave", ()),
        ("toggle_spectrogram", "toggle_spectrogram", ()),
        ("toggle_annotations", "toggle_annotations", ()),
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


# --------------------------- waveform context menu actions ---------------------------


def test_waveform_menu_actions_in_requested_order(loaded_view: DocumentView):
    loaded_view.view_model.start_selection(2.0)
    loaded_view.view_model.continue_selection(3.0)
    loaded_view.view_model.set_mark(4.0)
    menu = loaded_view.wave_plots[0].getViewBox().menu
    menu.aboutToShow.emit()
    actions = menu.actions()

    ordered = [
        loaded_view.zoom_to_selection_action,
        loaded_view.deselect_action,
        loaded_view.recenter_action,
        loaded_view.set_mark_action,
        loaded_view.remove_mark_action,
        loaded_view.wave_plots[0].audio_info_action,
        loaded_view.wave_plots[0].resample_action,
        loaded_view.wave_plots[0].scale_action,
        loaded_view.wave_plots[0].reverse_action,
        loaded_view.wave_plots[0].filter_action,
        loaded_view.wave_plots[0].revert_action,
    ]
    positions = [actions.index(a) for a in ordered]
    assert positions == sorted(positions)


def test_deselect_action_clears_selection(loaded_view: DocumentView):
    loaded_view.view_model.start_selection(2.0)
    loaded_view.view_model.continue_selection(3.0)
    assert loaded_view.view_model.select_state.is_selected

    loaded_view.deselect_action.trigger()

    assert not loaded_view.view_model.select_state.is_selected


def test_non_waveform_plots_only_get_mark_actions(loaded_view: DocumentView):
    loaded_view.view_model.toggle_spectrogram()
    QApplication.processEvents()
    spec = next(
        p for p in loaded_view.document_plots if p not in loaded_view.wave_plots
    )
    spec.getViewBox().menu.aboutToShow.emit()
    actions = spec.getViewBox().menu.actions()

    assert loaded_view.set_mark_action in actions
    assert loaded_view.wave_plots[0].scale_action not in actions


def test_zoom_to_selection_action_present_only_with_selection(
    loaded_view: DocumentView,
):
    menu = loaded_view.wave_plots[0].getViewBox().menu

    menu.aboutToShow.emit()
    assert loaded_view.zoom_to_selection_action not in menu.actions()

    loaded_view.view_model.start_selection(2.0)
    loaded_view.view_model.continue_selection(3.0)
    menu.aboutToShow.emit()
    assert loaded_view.zoom_to_selection_action in menu.actions()
    menu.aboutToShow.emit()  # idempotent
    assert menu.actions().count(loaded_view.zoom_to_selection_action) == 1

    loaded_view.view_model.remove_selection()
    menu.aboutToShow.emit()
    assert loaded_view.zoom_to_selection_action not in menu.actions()


def test_menu_rows_do_not_overlap_with_selection(loaded_view: DocumentView):
    loaded_view.view_model.start_selection(2.0)
    loaded_view.view_model.continue_selection(3.0)
    menu = loaded_view.wave_plots[0].getViewBox().menu
    menu.popup(loaded_view.mapToGlobal(loaded_view.rect().center()))
    QApplication.processEvents()

    rects = [
        menu.actionGeometry(a)
        for a in menu.actions()
        if not a.isSeparator() and a.isVisible()
    ]
    rects.sort(key=lambda r: r.top())
    for upper, lower in pairwise(rects):
        assert upper.bottom() < lower.top()
    menu.hide()


def test_open_scale_dialog_scales_when_accepted(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        ScaleAudioDialog, "get_scale_value", staticmethod(lambda **kw: -3.0)
    )
    calls = []
    loaded_view.view_model.scale_audio = lambda s: calls.append(s)

    loaded_view.open_scale_dialog()

    assert calls == [-3.0]


def test_open_scale_dialog_cancelled_or_unloaded(
    view: DocumentView, loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        ScaleAudioDialog, "get_scale_value", staticmethod(lambda **kw: None)
    )
    calls = []
    loaded_view.view_model.scale_audio = lambda s: calls.append(s)

    loaded_view.open_scale_dialog()

    assert calls == []


def test_open_filter_dialog_filters_when_accepted(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    spec = FilterSpec(FilterType.LOWPASS, high=100.0)
    monkeypatch.setattr(
        FilterAudioDialog, "get_filter_spec", staticmethod(lambda fs: spec)
    )
    calls = []
    loaded_view.view_model.filter_audio = lambda s: calls.append(s)

    loaded_view.open_filter_dialog()

    assert calls == [spec]


def test_open_filter_dialog_cancelled_does_nothing(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        FilterAudioDialog, "get_filter_spec", staticmethod(lambda fs: None)
    )
    calls = []
    loaded_view.view_model.filter_audio = lambda s: calls.append(s)

    loaded_view.open_filter_dialog()

    assert calls == []


def test_wave_y_range_stays_centered_when_layout_rebuilds_after_y_zoom(
    view: DocumentView, document_view_model: DocumentViewModel
):
    """Paste Special (mono -> stereo) and Delete Channel (stereo -> mono)
    rebuild the wave plots; a persisted y zoom must not leave the new plot
    with pyqtgraph's default range pushed off-center by the limits."""
    document_view_model.load_from_samples(
        to_audio_state({0: AudioSignal(np.sin(np.arange(20000) / 10) * 0.8, 1000)})
    )
    QApplication.processEvents()
    view.wave_plots[0].adjust_y_scale(-1)
    QApplication.processEvents()
    zoomed = view.wave_plots[0].getViewBox().viewRange()[1]

    clip = AudioState({0: AudioChannelState(np.sin(np.arange(2000) / 10) * 0.3, 1000)})
    document_view_model.paste_special_new_channel_with_silence(1, 1.0, clip)
    QApplication.processEvents()
    assert view.wave_plots[0].getViewBox().viewRange()[1] == pytest.approx(zoomed)

    document_view_model.delete_channel(1)
    QApplication.processEvents()
    assert view.wave_plots[0].getViewBox().viewRange()[1] == pytest.approx(zoomed)


def test_paste_special_reverses_clip_when_requested(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    loaded_view.view_model.set_mark(1.0)
    monkeypatch.setattr(
        PasteSpecialDialog,
        "get_choice",
        staticmethod(
            lambda parent=None, new_channel_available=True: PasteSpecialChoice(
                new_channel_idx=1, insert_silence=True, reverse=True
            )
        ),
    )
    pasted = []
    loaded_view.view_model.paste_special_new_channel_with_silence = (
        lambda new_channel_idx, position, clip: pasted.append(clip)
    )
    original = np.array([1.0, 2.0, 3.0])
    clip = AudioState({0: AudioChannelState(original.copy(), 1000)})

    loaded_view.paste_special(clip)

    np.testing.assert_array_equal(pasted[0].channels[0].x, original[::-1])
    np.testing.assert_array_equal(clip.channels[0].x, original)  # not mutated


def test_delete_button_mouse_click_converts_to_mono(
    stereo_loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    """A real click reaches the button through its QGraphicsProxyWidget, which
    must not be destroyed while it is still handling the mouse release."""
    monkeypatch.setattr(
        DeleteChannelDialog, "confirm", staticmethod(lambda parent: True)
    )
    proxy = stereo_loaded_view.document_plots[1].delete_button_proxy
    graphics_widget = stereo_loaded_view.graphics_widget
    viewport_pos = graphics_widget.mapFromScene(proxy.sceneBoundingRect().center())

    QTest.mouseClick(
        graphics_widget.viewport(), Qt.MouseButton.LeftButton, pos=viewport_pos
    )
    QApplication.processEvents()

    assert stereo_loaded_view.view_model.stereo_channels() is None
    assert len(stereo_loaded_view.document_plots) == 1


# --------------------------- save TextGrid ---------------------------


def stub_dialog(monkeypatch: pytest.MonkeyPatch, result: object, args: list):
    def get_options(*a: object) -> object:
        args.append(a)
        return result

    monkeypatch.setattr(SaveTextGridDialog, "get_options", staticmethod(get_options))


def test_save_textgrid_action_opens_save_textgrid_dialog(
    view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    calls = []
    monkeypatch.setattr(view, "open_save_textgrid", lambda: calls.append(True))

    view.on_state_change(SaveToTextGridAction())

    assert calls == [True]


def test_add_tiers_action_asks_which_tiers_and_adds_them(
    view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    asked: list = []
    added: list = []

    def get_names(
        available: list[str], existing: list[str], parent: object
    ) -> list[str]:
        asked.append((available, existing))
        return ["word", "tone"]

    monkeypatch.setattr(AddTiersDialog, "get_names", staticmethod(get_names))
    monkeypatch.setattr(view.view_model, "add_tiers", added.append)

    view.on_state_change(AddTiersAction(["word", "break"], ["break"]))

    assert asked == [(["word", "break"], ["break"])]
    assert added == [["word", "tone"]]


def test_add_tiers_adds_nothing_when_the_dialog_is_cancelled(
    view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    added: list = []
    monkeypatch.setattr(
        AddTiersDialog, "get_names", staticmethod(lambda *args, **kwargs: None)
    )
    monkeypatch.setattr(view.view_model, "add_tiers", added.append)

    view.on_state_change(AddTiersAction(["word"], []))

    assert added == []


def test_open_add_tiers_asks_the_view_model_to_start_adding_tiers(
    view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    calls: list = []
    monkeypatch.setattr(
        view.view_model, "trigger_add_tiers", lambda: calls.append(True)
    )

    view.open_add_tiers()

    assert calls == [True]


def test_open_save_textgrid_defaults_to_origin_path_and_file_stem(
    view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    view.origin_path = "/data/clip.wav"
    view.view_model.file_stem = "clip"
    args = []
    stub_dialog(monkeypatch, None, args)

    view.open_save_textgrid()

    assert args == [("/data/clip.wav", "clip", view)]


def test_open_save_textgrid_uses_empty_defaults_without_origin_or_stem(
    view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    args = []
    stub_dialog(monkeypatch, None, args)

    view.open_save_textgrid()

    assert args[0][:2] == ("", "")


def test_open_save_textgrid_saves_with_chosen_options(
    view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    stub_dialog(monkeypatch, ("/tmp/out.TextGrid", "long"), [])
    calls = []
    view.view_model.save_textgrid = lambda *args: calls.append(args)

    view.open_save_textgrid()

    assert calls == [("/tmp/out.TextGrid", "long")]


def test_open_save_textgrid_does_not_save_when_dialog_cancelled(
    view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    stub_dialog(monkeypatch, None, [])
    calls = []
    view.view_model.save_textgrid = lambda *args: calls.append(args)

    view.open_save_textgrid()

    assert calls == []


def test_open_save_textgrid_reports_runtime_error(
    view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    stub_dialog(monkeypatch, ("/tmp/out.TextGrid", "short"), [])

    def fail(*args: object):
        raise RuntimeError("overlapping intervals")

    view.view_model.save_textgrid = fail
    errors = []
    monkeypatch.setattr(
        QMessageBox, "critical", staticmethod(lambda *a: errors.append(a))
    )

    view.open_save_textgrid()

    assert len(errors) == 1
    assert "overlapping intervals" in errors[0][2]


# --------------------------- annotation shortcut follows visibility ---------------------------


def test_annotation_shortcut_is_active_while_the_document_is_shown(
    all_plots_view: DocumentView,
):
    plot = plot_of(all_plots_view, AnnotationPlot)

    assert all_plots_view.isVisible()
    assert plot.create_label_action.isEnabled()


def test_annotation_shortcut_is_switched_off_when_the_document_is_hidden(
    all_plots_view: DocumentView,
):
    plot = plot_of(all_plots_view, AnnotationPlot)

    all_plots_view.hide()

    assert not plot.create_label_action.isEnabled()


def test_annotation_shortcut_comes_back_when_the_document_is_shown_again(
    all_plots_view: DocumentView,
):
    plot = plot_of(all_plots_view, AnnotationPlot)
    all_plots_view.hide()

    all_plots_view.show()

    assert plot.create_label_action.isEnabled()


def test_annotation_plot_added_to_a_hidden_document_starts_with_its_shortcut_off(
    loaded_view: DocumentView,
):
    loaded_view.hide()

    loaded_view.view_model.toggle_annotations()
    QApplication.processEvents()

    assert not plot_of(loaded_view, AnnotationPlot).create_label_action.isEnabled()


# --------------------------- row heights follow the graphics widget ---------------------------


def test_resizing_the_graphics_widget_resizes_the_plot_rows(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    calls = []
    monkeypatch.setattr(loaded_view, "apply_row_heights", lambda: calls.append(True))
    loaded_view.graphics_widget.resized.disconnect()
    loaded_view.graphics_widget.resized.connect(loaded_view.apply_row_heights)

    loaded_view.graphics_widget.resized.emit()

    assert calls == [True]


def plots_bottom(view: DocumentView) -> float:
    return max(plot.sceneBoundingRect().bottom() for plot in view.document_plots)


def test_a_document_built_while_hidden_fills_the_space_it_is_later_shown_in(
    qtbot: QtBot, document_view_model: DocumentViewModel
):
    """A tab opened in the background has its plots laid out while its page is still
    at the default size, and is only resized when first shown, after the window
    may have been made bigger"""
    view = DocumentView(document_view_model)
    qtbot.addWidget(view)
    view.resize(640, 480)
    document_view_model.load_from_samples(
        to_audio_state({0: AudioSignal(np.arange(20000, dtype=np.float64), 1000)})
    )
    document_view_model.toggle_annotations()
    QApplication.processEvents()
    assert not view.isVisible()

    view.resize(1000, 900)
    view.show()
    qtbot.waitExposed(view)
    QApplication.processEvents()

    space = view.graphics_widget.viewport().height()
    assert plots_bottom(view) > space - 40


# --------------------------- selections that start or end off the plots ---------------------------


def press_at(
    view: DocumentView,
    scene_pos: QPointF,
    button: Qt.MouseButton = Qt.MouseButton.LeftButton,
) -> None:
    """Press the mouse at a scene position. The event position is in the document
    view's own coordinates, which are offset from the graphics area's by its layout
    margin"""
    in_graphics_widget = view.graphics_widget.mapFromScene(scene_pos)
    pos = QPointF(view.graphics_widget.mapToParent(in_graphics_widget))
    view.mousePressEvent(
        QMouseEvent(
            QEvent.Type.MouseButtonPress,
            pos,
            button,
            button,
            Qt.KeyboardModifier.NoModifier,
        )
    )


def wave_rect(view: DocumentView) -> QRectF:
    return view.document_plots[0].sceneBoundingRect()


def test_press_in_the_margin_beside_a_plot_starts_a_selection(
    loaded_view: DocumentView,
):
    rect = wave_rect(loaded_view)

    press_at(loaded_view, QPointF(rect.right() + 4, rect.center().y()))

    assert loaded_view.mouse_pressed is True


def test_press_in_the_gap_between_plots_starts_a_selection(
    all_plots_view: DocumentView,
):
    wave, sgram = all_plots_view.document_plots[0], all_plots_view.document_plots[1]
    gap_y = (wave.sceneBoundingRect().bottom() + sgram.sceneBoundingRect().top()) / 2
    assert all_plots_view._get_document_plot_at(QPointF(300, gap_y)) is None

    press_at(all_plots_view, QPointF(300, gap_y))

    assert all_plots_view.mouse_pressed is True


def test_press_in_the_top_margin_starts_a_selection(loaded_view: DocumentView):
    rect = wave_rect(loaded_view)

    press_at(loaded_view, QPointF(rect.center().x(), rect.top() - 4))

    assert loaded_view.mouse_pressed is True


def test_press_outside_the_graphics_area_does_not_start_a_selection(
    loaded_view: DocumentView,
):
    press_at(loaded_view, QPointF(-500, -500))

    assert loaded_view.mouse_pressed is False


@pytest.mark.parametrize(
    "button",
    [
        Qt.MouseButton.MiddleButton,
        Qt.MouseButton.BackButton,
        Qt.MouseButton.RightButton,
    ],
)
def test_only_the_left_button_starts_a_selection(
    loaded_view: DocumentView, button: Qt.MouseButton
):
    """A selection is ended by the release of the left button, so a press by any
    other button would leave it running for ever"""
    press_at(loaded_view, scene_center(loaded_view.document_plots[0]), button)

    assert loaded_view.mouse_pressed is False


def test_a_drag_keeps_selecting_when_the_pointer_leaves_the_plots(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(loaded_view, "left_button_is_down", lambda: True)
    plot = loaded_view.document_plots[0]
    rect = plot.sceneBoundingRect()
    press_at(loaded_view, scene_center(plot))
    loaded_view.on_mouse_moved(scene_center(plot))
    inside_end = loaded_view.view_model.select_state.sel_end

    # Dragged out past the right edge of the plot, over the margin
    loaded_view.on_mouse_moved(QPointF(rect.right() + 6, rect.center().y()))

    state = loaded_view.view_model.select_state
    assert state.sel_end > inside_end
    assert state.sel_start == pytest.approx(state.sel_anchor)


def test_a_drag_out_of_the_window_ends_at_the_end_of_the_audio(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(loaded_view, "left_button_is_down", lambda: True)
    plot = loaded_view.document_plots[0]
    press_at(loaded_view, scene_center(plot))
    loaded_view.on_mouse_moved(scene_center(plot))

    loaded_view.on_mouse_moved(QPointF(5000, plot.sceneBoundingRect().center().y()))

    channel = loaded_view.view_model.primary_channel()
    assert channel is not None
    assert loaded_view.view_model.select_state.sel_end == pytest.approx(channel.t[-1])


def test_moving_with_no_button_down_shows_status_and_does_not_select(
    loaded_view: DocumentView,
):
    loaded_view.message_label.setText("")
    rect = wave_rect(loaded_view)

    loaded_view.on_mouse_moved(QPointF(rect.right() + 4, rect.center().y()))

    assert loaded_view.view_model.select_state.is_selected is False
    assert loaded_view.message_label.text() == ""  # off the plots: no cursor time


# --------------------------- a release that never arrives ---------------------------


def test_a_missing_release_is_made_up_when_the_pointer_moves_without_the_button(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    plot = loaded_view.document_plots[0]
    held = {"down": True}
    monkeypatch.setattr(loaded_view, "left_button_is_down", lambda: held["down"])
    press_at(loaded_view, scene_center(plot))
    loaded_view.on_mouse_moved(scene_center(plot))
    loaded_view.on_mouse_moved(scene_center(plot) + QPointF(30, 0))
    assert loaded_view.is_dragging is True
    selection = loaded_view.view_model.select_state

    held["down"] = False  # the release was lost
    loaded_view.on_mouse_moved(scene_center(plot) + QPointF(80, 0))

    assert loaded_view.mouse_pressed is False
    assert loaded_view.is_dragging is False
    assert loaded_view.view_model.select_state == selection  # no longer following
    assert len(loaded_view.view_model.audio_player.played) == 1


def test_the_selection_keeps_following_the_pointer_while_the_button_is_down(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(loaded_view, "left_button_is_down", lambda: True)
    plot = loaded_view.document_plots[0]
    press_at(loaded_view, scene_center(plot))
    loaded_view.on_mouse_moved(scene_center(plot))

    loaded_view.on_mouse_moved(scene_center(plot) + QPointF(40, 0))
    first_end = loaded_view.view_model.select_state.sel_end
    loaded_view.on_mouse_moved(scene_center(plot) + QPointF(90, 0))

    assert loaded_view.mouse_pressed is True
    assert loaded_view.view_model.select_state.sel_end > first_end
    assert loaded_view.view_model.audio_player.played == []


def test_a_lost_release_after_a_click_without_drag_is_treated_as_a_click(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(loaded_view, "left_button_is_down", lambda: False)
    plot = loaded_view.document_plots[0]
    press_scene = scene_center(plot)
    press_at(loaded_view, press_scene)

    loaded_view.on_mouse_moved(press_scene + QPointF(5, 0))

    assert loaded_view.mouse_pressed is False
    assert loaded_view.pending_single_click == loaded_view.press_scene_pos
    assert loaded_view.view_model.select_state.is_selected is False


def test_left_button_is_down_reads_the_application_state(
    loaded_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        QApplication, "mouseButtons", staticmethod(lambda: Qt.MouseButton.LeftButton)
    )
    assert loaded_view.left_button_is_down() is True

    monkeypatch.setattr(
        QApplication, "mouseButtons", staticmethod(lambda: Qt.MouseButton.RightButton)
    )
    assert loaded_view.left_button_is_down() is False


# --------------------------- mouse-move connections ---------------------------


def move_receivers(view: DocumentView) -> int:
    scene = view.graphics_widget.scene()
    return scene.receivers(scene.sigMouseMoved)


def test_rebuilding_the_layout_does_not_add_mouse_move_connections(
    loaded_view: DocumentView,
):
    before = move_receivers(loaded_view)

    for _ in range(3):
        loaded_view.view_model.toggle_spectrogram()
        QApplication.processEvents()
        loaded_view.view_model.toggle_spectrogram()
        QApplication.processEvents()

    assert move_receivers(loaded_view) == before == 1


def test_a_mouse_move_reaches_each_plot_once(
    all_plots_view: DocumentView, monkeypatch: pytest.MonkeyPatch
):
    calls: list[int] = []
    for index, plot in enumerate(all_plots_view.document_plots):
        monkeypatch.setattr(
            plot, "on_mouse_moved", lambda pos, index=index: calls.append(index)
        )

    all_plots_view.on_mouse_moved(QPointF(300, 100))

    assert sorted(calls) == [0, 1, 2]
