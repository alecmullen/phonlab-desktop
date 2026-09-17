from pathlib import Path

import numpy as np
import pytest
from PyQt6.QtCore import QObject, pyqtSignal
from pytestqt.qtbot import QtBot

import ui.base.view_model as view_model_module
import ui.document.document_view_model as dvm_module
from core.load_audio.entity.audio_open_options import AudioOpenOptions
from core.load_audio.entity.audio_signal import AudioSignal
from core.settings.app_settings import settings
from ui.document.document_view_model import DocumentViewModel
from ui.document.state.audio_channel_state import AudioChannelState
from ui.document.state.audio_loaded import AudioLoaded
from ui.document.state.document_window_state import DocumentWindowState
from ui.document.state.edit_command_state import EditCommandState
from ui.document.state.load_progress_state import LoadProgressState
from ui.document.state.mark_state import MarkState
from ui.document.state.plot_layout_state import PlotType
from ui.document.state.select_state import SelectState
from ui.document.state.status_message_state import StatusMessageState
from ui.spectrogram.state.audio_prepped import AudioPrepped


class FakeAudioPlayer:
    def __init__(self):
        self.stopped = False
        self.played: list[tuple[np.ndarray, int, float]] = []

    def stop(self):
        self.stopped = True

    def play(self, x: np.ndarray, fs: int, start: float):
        self.played.append((x, fs, start))

    class playback_poll:
        @staticmethod
        def connect(slot: object):
            pass


class FakeJobManagerSignals(QObject):
    finished = pyqtSignal()


class FakeJobManager:
    def __init__(self):
        self.signals = FakeJobManagerSignals()
        self.jobs = []

    def __call__(self, job: object):
        self.jobs.append(job)

    def queue_job(self, job: object):
        self.jobs.append(job)

    def quit(self):
        pass


@pytest.fixture
def view_model(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> DocumentViewModel:
    monkeypatch.setattr(dvm_module, "AudioPlayer", FakeAudioPlayer)
    vm = DocumentViewModel()
    # Do not trigger spectrogram
    vm.prep_audio_spectrogram = lambda: None
    return vm


def load_signal(
    view_model: DocumentViewModel, x: np.ndarray, fs: int
) -> AudioChannelState:
    return view_model.set_audio(
        {0: AudioChannelState(np.asarray(x, dtype=np.float64), fs)},
        primary_channel_idx=0,
        reset_window=True,
    )


# --------------------------- navigation ---------------------------


def test_set_audio_resets_window_to_default_length(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(50000), fs=1000)

    assert view_model.document_window_state == DocumentWindowState(
        start=0, end=10000, max_start=39999
    )


def test_go_back_clamps_at_start(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(50000), fs=1000)

    view_model.go_back()

    assert view_model.document_window_state.start == 0
    assert view_model.document_window_state.end == 10000


def test_advance_moves_window_forward_by_window_size(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(50000), fs=1000)

    view_model.advance()

    assert view_model.document_window_state.start == 10000
    assert view_model.document_window_state.end == 20000


def test_move_start_clamps_to_signal_end(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(15000), fs=1000)

    view_model.move_start(100000)

    assert view_model.document_window_state.end == 14999
    assert view_model.document_window_state.start == 4999


def test_move_start_by_fraction_scrolls_proportionally(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(50000), fs=1000)

    view_model.move_start_by_fraction(0.5)

    assert view_model.document_window_state.start == 5000
    assert view_model.document_window_state.end == 15000


def test_zoom_out_doubles_window_and_recenters(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(50000), fs=1000)
    view_model.advance()

    view_model.zoom_out()

    window = view_model.document_window_state
    assert window.end - window.start == 20000


def test_zoom_in_halves_window_and_recenters(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(50000), fs=1000)

    view_model.zoom_in()

    window = view_model.document_window_state
    assert window.end - window.start == 5000


def test_zoom_in_does_not_shrink_window_below_minimum_size(
    view_model: DocumentViewModel,
):
    load_signal(view_model, np.arange(50000), fs=1000)
    view_model.document_window_state = DocumentWindowState(
        start=0, end=100, max_start=49900
    )

    view_model.zoom_in(factor=10)

    window = view_model.document_window_state
    assert window.end - window.start == 50


def test_show_all_sets_window_to_full_signal(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(50000), fs=1000)

    view_model.show_all()

    assert view_model.document_window_state == DocumentWindowState(start=0, end=49999)


def test_adjust_window_if_needed_shrinks_window_to_new_signal_end(
    view_model: DocumentViewModel,
):
    load_signal(view_model, np.arange(10000), fs=1000)

    view_model.adjust_window_if_needed(5000)

    assert view_model.document_window_state.start == 0
    assert view_model.document_window_state.end == 5000


def test_center_on_selection_centers_window_on_selection_midpoint(
    view_model: DocumentViewModel,
):
    load_signal(view_model, np.arange(50000), fs=1000)
    view_model.start_selection(20.0)
    view_model.continue_selection(30.0)

    view_model.center_on_selection()

    window = view_model.document_window_state
    center = (window.start + window.end) / 2
    assert center == pytest.approx(25000, abs=1)


def test_center_on_selection_shows_status_message_when_nothing_selected(
    view_model: DocumentViewModel,
):
    load_signal(view_model, np.arange(50000), fs=1000)
    received = []
    view_model.subscribe(received.append)

    view_model.center_on_selection()

    assert any(isinstance(s, StatusMessageState) for s in received)


def test_zoom_if_in_selection_zooms_to_selection_when_click_inside(
    view_model: DocumentViewModel,
):
    load_signal(view_model, np.arange(50000), fs=1000)
    view_model.start_selection(1.0)
    view_model.continue_selection(5.0)

    view_model.zoom_if_in_selection(2.0)

    assert view_model.document_window_state.start == 1000
    assert view_model.document_window_state.end == 5000
    assert view_model.select_state.is_selected is False


def test_zoom_if_in_selection_does_nothing_when_click_outside(
    view_model: DocumentViewModel,
):
    load_signal(view_model, np.arange(50000), fs=1000)
    view_model.start_selection(1.0)
    view_model.continue_selection(5.0)
    window_before = view_model.document_window_state

    view_model.zoom_if_in_selection(10.0)

    assert view_model.document_window_state == window_before
    assert view_model.select_state.is_selected is True


# --------------------------- selection ---------------------------


def test_start_selection_sets_anchor_and_marks_selected(
    view_model: DocumentViewModel,
):
    load_signal(view_model, np.arange(5000), fs=1000)

    view_model.start_selection(1.5)

    assert view_model.select_state == SelectState(
        sel_start=1.5, sel_end=1.5, sel_anchor=1.5, is_selected=True
    )


def test_continue_selection_forward_from_anchor(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(5000), fs=1000)
    view_model.start_selection(1.0)

    view_model.continue_selection(3.0)

    assert view_model.select_state.sel_start == 1.0
    assert view_model.select_state.sel_end == 3.0


def test_continue_selection_backward_from_anchor(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(5000), fs=1000)
    view_model.start_selection(3.0)

    view_model.continue_selection(1.0)

    assert view_model.select_state.sel_start == 1.0
    assert view_model.select_state.sel_end == 3.0


def test_continue_selection_clamps_to_channel_duration(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(5000), fs=1000)
    channel_end = view_model.primary_channel().t[-1]
    view_model.start_selection(2.0)

    view_model.continue_selection(100.0)

    assert view_model.select_state.sel_end == channel_end


def test_continue_selection_clamps_to_zero(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(5000), fs=1000)
    view_model.start_selection(2.0)

    view_model.continue_selection(-50.0)

    assert view_model.select_state.sel_start == 0.0


def test_remove_selection_resets_to_default(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(5000), fs=1000)
    view_model.start_selection(2.0)

    view_model.remove_selection()

    assert view_model.select_state == SelectState()


# --------------------------- mark ---------------------------


def test_set_mark_records_position(view_model: DocumentViewModel):
    view_model.set_mark(3.5)

    assert view_model.mark_state == MarkState(position=3.5, is_set=True)


def test_remove_mark_resets_to_default(view_model: DocumentViewModel):
    view_model.set_mark(3.5)

    view_model.remove_mark()

    assert view_model.mark_state == MarkState()


# --------------------------- plot layout ---------------------------


def test_toggle_wave_removes_waveform_when_another_plot_present(
    view_model: DocumentViewModel,
):
    view_model.update_spectrogram = lambda: None
    view_model.toggle_spectrogram()

    view_model.toggle_wave()

    assert PlotType.WAVEFORM not in view_model.plot_layout_state.plots
    assert PlotType.SPECTROGRAM in view_model.plot_layout_state.plots


def test_toggle_wave_keeps_last_remaining_plot(view_model: DocumentViewModel):
    view_model.toggle_wave()

    assert view_model.plot_layout_state.plots == {PlotType.WAVEFORM}


def test_toggle_spectrogram_adds_and_removes_spectrogram(
    view_model: DocumentViewModel,
):
    view_model.update_spectrogram = lambda: None

    view_model.toggle_spectrogram()
    assert PlotType.SPECTROGRAM in view_model.plot_layout_state.plots

    view_model.toggle_spectrogram()
    assert PlotType.SPECTROGRAM not in view_model.plot_layout_state.plots


def test_toggle_annotations_adds_and_removes_annotations(
    view_model: DocumentViewModel,
):
    view_model.update_annotation_state = lambda: None

    view_model.toggle_annotations()
    assert PlotType.ANNOTATION in view_model.plot_layout_state.plots

    view_model.toggle_annotations()
    assert PlotType.ANNOTATION not in view_model.plot_layout_state.plots


# --------------------------- primary_channel ---------------------------


def test_primary_channel_is_none_without_loaded_audio(view_model: DocumentViewModel):
    assert view_model.primary_channel() is None


def test_primary_channel_returns_channel_for_current_primary_index(
    view_model: DocumentViewModel,
):
    load_signal(view_model, np.arange(1000), fs=500)

    channel = view_model.primary_channel()

    assert channel is not None
    assert channel.fs == 500
    assert len(channel.x) == 1000


# --------------------------- editing: copy/cut/paste/undo/redo ---------------------------


@pytest.fixture(autouse=True)
def disable_zero_crossing_snapping(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)


def test_copy_selection_returns_selected_slice(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(10000), fs=1000)
    view_model.start_selection(2.0)
    view_model.continue_selection(3.0)

    clip = view_model.copy_selection()

    assert clip is not None
    np.testing.assert_array_equal(clip.x, np.arange(2000, 3000))
    assert len(view_model.primary_channel().x) == 10000


def test_copy_selection_returns_none_when_audio_not_loaded(
    view_model: DocumentViewModel,
):
    assert view_model.copy_selection() is None


def test_copy_selection_returns_none_when_nothing_selected(
    view_model: DocumentViewModel,
):
    load_signal(view_model, np.arange(10000), fs=1000)

    assert view_model.copy_selection() is None


def test_cut_selection_removes_slice_and_pushes_undo(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(10000), fs=1000)
    view_model.start_selection(2.0)
    view_model.continue_selection(3.0)

    clip = view_model.cut_selection()

    assert clip is not None
    np.testing.assert_array_equal(clip.x, np.arange(2000, 3000))
    assert len(view_model.primary_channel().x) == 9000
    assert len(view_model.undo_stack) == 1
    assert view_model.undo_stack[0].type == "cut"


def test_undo_restores_cut_audio(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(10000), fs=1000)
    view_model.start_selection(2.0)
    view_model.continue_selection(3.0)
    view_model.cut_selection()

    view_model.undo()

    np.testing.assert_array_equal(view_model.primary_channel().x, np.arange(10000))
    assert view_model.undo_stack == []
    assert len(view_model.redo_stack) == 1


def test_redo_reapplies_undone_cut(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(10000), fs=1000)
    view_model.start_selection(2.0)
    view_model.continue_selection(3.0)
    view_model.cut_selection()
    view_model.undo()

    view_model.redo()

    assert len(view_model.primary_channel().x) == 9000
    assert len(view_model.undo_stack) == 1
    assert view_model.redo_stack == []


def test_undo_with_empty_stack_is_a_noop(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(10000), fs=1000)

    view_model.undo()

    assert len(view_model.primary_channel().x) == 10000


def test_redo_with_empty_stack_is_a_noop(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(10000), fs=1000)

    view_model.redo()

    assert len(view_model.primary_channel().x) == 10000


def test_paste_at_mark_inserts_clip_at_mark_position(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(10000), fs=1000)
    clip = AudioSignal(np.full(500, -1.0), fs=1000)
    view_model.set_mark(1.0)

    view_model.paste_at_mark(clip)

    channel = view_model.primary_channel()
    assert len(channel.x) == 10500
    np.testing.assert_array_equal(channel.x[1000:1500], np.full(500, -1.0))
    assert len(view_model.undo_stack) == 1
    assert view_model.undo_stack[0].type == "paste"


def test_paste_at_mark_shows_message_when_mark_not_set(
    view_model: DocumentViewModel,
):
    load_signal(view_model, np.arange(10000), fs=1000)
    received = []
    view_model.subscribe(received.append)
    clip = AudioSignal(np.full(500, -1.0), fs=1000)

    view_model.paste_at_mark(clip)

    assert len(view_model.primary_channel().x) == 10000
    assert any(isinstance(s, StatusMessageState) for s in received)


def test_push_undo_caps_history_and_clears_redo(view_model: DocumentViewModel):
    view_model.redo_stack.append(EditCommandState("cut", 0, np.array([])))

    for i in range(15):
        view_model._push_undo(EditCommandState("cut", i, np.array([])))

    assert len(view_model.undo_stack) == 10
    assert view_model.undo_stack[0].start_idx == 5
    assert view_model.redo_stack == []


# --------------------------- load_audio / resample (async use cases) ---------------------------


def test_load_audio_launches_use_case_and_updates_state_on_success(
    view_model: DocumentViewModel, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(view_model_module, "JobManager", FakeJobManager)
    received = []
    view_model.subscribe(received.append)
    options = AudioOpenOptions(primary_channel=0, channel_mode="mono")

    view_model.load_audio("/fake/path.wav", options)

    manager = view_model.job_managers["load_audio"]
    job = manager.jobs[0]

    signals = {0: AudioSignal(np.arange(20000, dtype=np.float64), 1000)}
    job.on_success(signals)

    assert view_model.audio_loaded_state == AudioLoaded(is_loaded=True, fs=1000)
    assert view_model.raw_audio_state.keys() == {0}
    assert any(isinstance(s, AudioLoaded) for s in received)


def test_resample_rescales_window_and_updates_primary_fs(
    view_model: DocumentViewModel, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(view_model_module, "JobManager", FakeJobManager)
    load_signal(view_model, np.arange(20000), fs=1000)
    view_model.raw_audio_state = view_model.audio_state.copy()

    view_model.resample(2000)

    manager = view_model.job_managers["prep_audio"]
    job = manager.jobs[0]
    prepped = {0: AudioSignal(np.arange(40000, dtype=np.float64), 2000)}

    job.on_success(prepped)

    assert view_model.primary_channel().fs == 2000
    assert view_model.document_window_state.start == 0
    assert view_model.document_window_state.end == 20000


# --------------------------- state dispatch ---------------------------


def test_on_state_changed_preps_spectrogram_on_audio_loaded(
    view_model: DocumentViewModel,
):
    calls = []
    view_model.prep_audio_spectrogram = lambda: calls.append(True)

    view_model.on_state_changed(AudioLoaded(True, 1000))

    assert calls == [True]


def test_on_state_changed_ignores_other_states(view_model: DocumentViewModel):
    calls = []
    view_model.prep_audio_spectrogram = lambda: calls.append(True)

    view_model.on_state_changed(StatusMessageState("hi"))

    assert calls == []


def test_on_sgram_state_change_forwards_load_progress_and_prepped(
    view_model: DocumentViewModel,
):
    received = []
    view_model.subscribe(received.append)

    view_model.on_sgram_state_change(LoadProgressState(True))
    view_model.on_sgram_state_change(AudioPrepped())
    view_model.on_sgram_state_change(StatusMessageState("ignored"))

    assert [type(s).__name__ for s in received] == ["LoadProgressState", "AudioPrepped"]


# --------------------------- misc ---------------------------


TEXTGRID_FIXTURE = """File type = "ooTextFile"
Object class = "TextGrid"
xmin = 0
xmax = 1.0
tiers? <exists>
size = 1
item []:
    item [1]:
        class = "IntervalTier"
        name = "word"
        xmin = 0
        xmax = 1.0
        intervals: size = 2
        intervals [1]:
            xmin = 0
            xmax = 0.5
            text = "hello"
        intervals [2]:
            xmin = 0.5
            xmax = 1.0
            text = "world"
"""


def test_parse_textgrid_loads_annotation_state(
    view_model: DocumentViewModel, tmp_path: Path
):
    load_signal(view_model, np.arange(5000), fs=1000)
    view_model.update_annotation_state = lambda: None
    textgrid = tmp_path / "sample.TextGrid"
    textgrid.write_text(TEXTGRID_FIXTURE)

    view_model.parse_textgrid(str(textgrid))

    assert view_model.annotation_state.nodes == {0: 0.0, 1: 0.5, 2: 1.0}
    assert [t.type for t in view_model.annotation_state.types] == ["word"]
    assert [label.label for label in view_model.annotation_state.types[0].labels] == [
        "hello",
        "world",
    ]


def test_play_selected_audio_plays_selection(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(10000), fs=1000)
    view_model.start_selection(2.0)
    view_model.continue_selection(4.0)

    view_model.play_selected_audio()

    assert len(view_model.audio_player.played) == 1
    x, fs, start = view_model.audio_player.played[0]
    assert len(x) == 2000
    assert fs == 1000
    assert start == 2.0


def test_play_selected_audio_does_nothing_for_zero_length_selection(
    view_model: DocumentViewModel,
):
    load_signal(view_model, np.arange(10000), fs=1000)

    view_model.play_selected_audio()

    assert view_model.audio_player.played == []


def test_play_selected_audio_shows_message_when_audio_not_loaded(
    view_model: DocumentViewModel,
):
    received = []
    view_model.subscribe(received.append)

    view_model.play_selected_audio()

    assert view_model.audio_player.played == []
    assert any(isinstance(s, StatusMessageState) for s in received)


def test_play_visible_audio_plays_current_window(view_model: DocumentViewModel):
    load_signal(view_model, np.arange(50000), fs=1000)

    view_model.play_visible_audio()

    assert len(view_model.audio_player.played) == 1
    x, _fs, start = view_model.audio_player.played[0]
    assert len(x) == 10000
    assert start == 0.0


def test_close_threads_stops_audio_player(view_model: DocumentViewModel):
    view_model.close_threads()

    assert view_model.audio_player.stopped is True
