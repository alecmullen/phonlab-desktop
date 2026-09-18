from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
from PyQt6.QtCore import QEvent, QObject, Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

import ui.base.view_model as view_model_module
import ui.document.document_view_model as dvm_module
import ui.main.main_window as main_window_module
from core.load_audio.entity.audio_open_options import AudioOpenOptions
from core.load_audio.entity.audio_signal import AudioSignal
from core.settings.app_settings import settings
from ui.document.document_view import DocumentView
from ui.document.document_view_model import DocumentViewModel
from ui.document.state.audio_channel_state import AudioChannelState
from ui.main.main_window import MainWindow
from ui.main.open_audio_dialog import OpenAudioDialog
from ui.main.save_audio_dialog import SaveOptions


class FakeAudioPlayer:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True

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


@pytest.fixture(autouse=True)
def disable_zero_crossing_snapping(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)


@pytest.fixture
def main_window(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> MainWindow:
    monkeypatch.setattr(dvm_module, "AudioPlayer", FakeAudioPlayer)
    monkeypatch.setattr(view_model_module, "JobManager", FakeJobManager)
    win = MainWindow()
    qtbot.addWidget(win)
    return win


def add_document(main_window: MainWindow, name: str = "doc.wav") -> DocumentView:
    vm = DocumentViewModel()
    vm.prep_audio_spectrogram = lambda: None
    doc = DocumentView(vm)
    doc.origin_name = name
    doc.origin_path = f"/tmp/{name}"
    main_window.tab_widget.addTab(doc, name)
    main_window.tab_widget.setCurrentIndex(main_window.tab_widget.count() - 1)
    return doc


def load_signal(doc: DocumentView, x: np.ndarray, fs: int):
    doc.view_model.set_audio(
        {0: AudioChannelState(np.asarray(x, dtype=np.float64), fs)},
        primary_channel_idx=0,
        reset_window=True,
    )


# --------------------------- basic construction ---------------------------


def test_starts_with_no_tabs_and_disabled_spectrogram_action(main_window: MainWindow):
    assert main_window.tab_widget.count() == 0
    assert main_window.sgramview_action.isEnabled() is False


def test_get_current_document_is_none_without_tabs(main_window: MainWindow):
    assert main_window.get_current_document() is None


def test_get_current_document_returns_active_tab(main_window: MainWindow):
    doc = add_document(main_window)

    assert main_window.get_current_document() is doc


# --------------------------- open_files ---------------------------


def test_open_files_creates_a_tab_and_loads_audio(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    wav_path = tmp_path / "sound.wav"
    wav_path.write_bytes(b"")
    monkeypatch.setattr(
        OpenAudioDialog,
        "get_options",
        staticmethod(lambda filename, parent=None: AudioOpenOptions()),
    )

    main_window.open_files([str(wav_path)])

    assert main_window.tab_widget.count() == 1
    assert main_window.tab_widget.tabText(0) == "sound.wav"
    doc = main_window.get_current_document()
    assert doc.origin_name == "sound.wav"
    assert doc.origin_path == str(wav_path)
    assert "load_audio" in doc.view_model.job_managers


def test_open_files_also_loads_a_paired_textgrid(
    main_window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    wav_path = tmp_path / "sound.wav"
    wav_path.write_bytes(b"")
    textgrid_path = tmp_path / "sound.TextGrid"
    textgrid_path.write_text(
        'File type = "ooTextFile"\n'
        'Object class = "TextGrid"\n'
        "xmin = 0\nxmax = 1.0\n"
        "tiers? <exists>\nsize = 1\nitem []:\n"
        "    item [1]:\n"
        '        class = "IntervalTier"\n'
        '        name = "word"\n'
        "        xmin = 0\nxmax = 1.0\n"
        "        intervals: size = 1\n"
        "        intervals [1]:\n"
        "            xmin = 0\nxmax = 1.0\n"
        '            text = "hi"\n'
    )
    monkeypatch.setattr(
        OpenAudioDialog,
        "get_options",
        staticmethod(lambda filename, parent=None: AudioOpenOptions()),
    )

    main_window.open_files([str(wav_path), str(textgrid_path)])

    doc = main_window.get_current_document()
    assert doc.view_model.annotation_state.nodes == {0: 0.0, 1: 1.0}


def test_open_files_does_nothing_when_dialog_is_cancelled(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    wav_path = tmp_path / "sound.wav"
    wav_path.write_bytes(b"")
    monkeypatch.setattr(
        OpenAudioDialog, "get_options", staticmethod(lambda filename, parent=None: None)
    )

    main_window.open_files([str(wav_path)])

    assert main_window.tab_widget.count() == 0


def test_open_files_does_nothing_without_a_wav_file(
    main_window: MainWindow, tmp_path: Path
):
    textgrid_path = tmp_path / "only.TextGrid"
    textgrid_path.write_text("")

    main_window.open_files([str(textgrid_path)])

    assert main_window.tab_widget.count() == 0


def test_open_files_closes_splash_screen(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    wav_path = tmp_path / "sound.wav"
    wav_path.write_bytes(b"")
    monkeypatch.setattr(
        OpenAudioDialog,
        "get_options",
        staticmethod(lambda filename, parent=None: AudioOpenOptions()),
    )
    closed = []
    main_window.splash = type(
        "FakeSplash", (), {"close": lambda self: closed.append(True)}
    )()

    main_window.open_files([str(wav_path)])

    assert closed == [True]
    assert main_window.splash is None


# --------------------------- copy/cut open a clip tab ---------------------------


def test_copy_selection_opens_a_clip_tab_and_sets_clipboard(main_window: MainWindow):
    doc = add_document(main_window, "source.wav")
    load_signal(doc, np.arange(10000), fs=1000)
    doc.view_model.start_selection(2.0)
    doc.view_model.continue_selection(3.0)

    main_window.copy_selection()

    assert main_window.tab_widget.count() == 2
    assert main_window.tab_widget.tabText(1) == "CLIP 1: source.wav"
    assert main_window.clipboard is not None
    assert len(main_window.clipboard.x) == 1000


def test_cut_selection_opens_a_clip_tab_and_sets_clipboard(main_window: MainWindow):
    doc = add_document(main_window, "source.wav")
    load_signal(doc, np.arange(10000), fs=1000)
    doc.view_model.start_selection(2.0)
    doc.view_model.continue_selection(3.0)

    main_window.cut_selection()

    assert main_window.tab_widget.count() == 2
    assert main_window.clipboard is not None
    assert len(doc.view_model.primary_channel().x) == 9000


def test_repeated_clips_from_same_source_increment_clip_counter(
    main_window: MainWindow,
):
    doc = add_document(main_window, "source.wav")
    load_signal(doc, np.arange(10000), fs=1000)
    doc.view_model.start_selection(1.0)
    doc.view_model.continue_selection(2.0)
    main_window.copy_selection()

    main_window.tab_widget.setCurrentWidget(doc)
    doc.view_model.start_selection(3.0)
    doc.view_model.continue_selection(4.0)
    main_window.copy_selection()

    assert main_window.tab_widget.tabText(1) == "CLIP 1: source.wav"
    assert main_window.tab_widget.tabText(2) == "CLIP 2: source.wav"


def test_copy_selection_does_nothing_without_a_selection(main_window: MainWindow):
    doc = add_document(main_window, "source.wav")
    load_signal(doc, np.arange(10000), fs=1000)

    main_window.copy_selection()

    assert main_window.tab_widget.count() == 1
    assert main_window.clipboard is None


# --------------------------- tab lifecycle ---------------------------


def test_close_tab_cleans_up_and_removes_it(main_window: MainWindow):
    doc = add_document(main_window)

    main_window.close_tab(0)

    assert main_window.tab_widget.count() == 0
    assert doc.view_model.audio_player.stopped is True


def test_close_current_tab_closes_the_active_tab(main_window: MainWindow):
    add_document(main_window, "a.wav")
    add_document(main_window, "b.wav")

    main_window.close_current_tab()

    assert main_window.tab_widget.count() == 1
    assert main_window.tab_widget.tabText(0) == "a.wav"


def test_close_current_tab_is_a_noop_without_tabs(main_window: MainWindow):
    main_window.close_current_tab()

    assert main_window.tab_widget.count() == 0


def test_on_tab_changed_enables_spectrogram_action_when_prepped(
    main_window: MainWindow,
):
    doc = add_document(main_window)
    doc.view_model.spectrogram_view_model.prepped_audio_state = object()

    main_window.on_tab_changed(0)

    assert main_window.sgramview_action.isEnabled() is True


def test_on_tab_changed_disables_spectrogram_action_when_not_prepped(
    main_window: MainWindow,
):
    add_document(main_window)

    main_window.on_tab_changed(0)

    assert main_window.sgramview_action.isEnabled() is False


# --------------------------- delegation to current document ---------------------------


@pytest.mark.parametrize(
    "action,doc_method",
    [
        (lambda w: w.plot_wave(), "toggle_wave"),
        (lambda w: w.plot_wave_sgram(), "toggle_spectrogram"),
        (lambda w: w.plot_annotations(), "toggle_annotations"),
        (lambda w: w.show_all(), "show_all"),
        (lambda w: w.play_visible(), "play_visible"),
        (lambda w: w.stop_audio(), "stop_audio"),
        (lambda w: w.recenter_on_selection(), "recenter_on_selection"),
        (lambda w: w.undo(), "undo"),
        (lambda w: w.redo(), "redo"),
    ],
)
def test_delegates_to_current_document(
    main_window: MainWindow, action: Callable[[MainWindow], None], doc_method: str
):
    doc = add_document(main_window)
    calls = []
    setattr(doc, doc_method, lambda: calls.append(True))

    action(main_window)

    assert calls == [True]


@pytest.mark.parametrize(
    "action",
    [
        lambda w: w.plot_wave(),
        lambda w: w.show_all(),
        lambda w: w.play_visible(),
        lambda w: w.undo(),
        lambda w: w.redo(),
    ],
)
def test_delegation_is_a_noop_without_a_current_document(
    main_window: MainWindow, action: Callable[[MainWindow], None]
):
    # Should not raise even though there is no active document.
    action(main_window)


def test_paste_at_cursor_forwards_clipboard_to_document(main_window: MainWindow):
    doc = add_document(main_window)
    calls = []
    doc.paste_at_cursor = lambda clip: calls.append(clip)
    main_window.clipboard = AudioSignal(np.array([1.0, 2.0]), 1000)

    main_window.paste_at_cursor()

    assert len(calls) == 1
    assert calls[0] is main_window.clipboard


def test_paste_at_cursor_does_nothing_without_a_clipboard(main_window: MainWindow):
    doc = add_document(main_window)
    calls = []
    doc.paste_at_cursor = lambda clip: calls.append(clip)

    main_window.paste_at_cursor()

    assert calls == []


# --------------------------- keyboard navigation ---------------------------


@pytest.mark.parametrize(
    "key,doc_method",
    [
        (Qt.Key.Key_Left, "go_back"),
        (Qt.Key.Key_Right, "advance"),
        (Qt.Key.Key_Down, "zoom_out"),
        (Qt.Key.Key_Up, "zoom_in"),
    ],
)
def test_key_press_forwards_navigation_to_current_document(
    main_window: MainWindow, key: Qt.Key, doc_method: str
):
    doc = add_document(main_window)
    calls = []
    setattr(doc, doc_method, lambda: calls.append(True))
    event = QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)

    main_window.keyPressEvent(event)

    assert calls == [True]


def test_key_press_for_unhandled_key_does_not_touch_document(main_window: MainWindow):
    doc = add_document(main_window)
    calls = []
    doc.go_back = lambda: calls.append(True)
    event = QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier
    )

    main_window.keyPressEvent(event)

    assert calls == []


# --------------------------- save / info dialogs ---------------------------


def test_save_audio_invokes_save_use_case_with_selected_options(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
):
    doc = add_document(main_window, "myfile.wav")
    load_signal(doc, np.arange(5000), fs=1000)
    monkeypatch.setattr(
        main_window_module.SaveAudioDialog,
        "get_options",
        staticmethod(
            lambda doc, name, parent=None: SaveOptions(
                path="/tmp/out.wav", target_fs=8000, scale=True
            )
        ),
    )
    calls = []

    class FakeSaveAudio:
        def __init__(
            self, path: str, x: np.ndarray, fs: int, target_fs: int, scale: bool
        ):
            calls.append((path, fs, target_fs, scale))

        def invoke(self):
            pass

    monkeypatch.setattr(main_window_module, "SaveAudio", FakeSaveAudio)

    main_window.save_audio()

    assert calls == [("/tmp/out.wav", 1000, 8000, True)]


def test_save_audio_does_nothing_without_a_current_document(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
):
    calls = []
    monkeypatch.setattr(
        main_window_module.SaveAudioDialog,
        "get_options",
        staticmethod(lambda doc, name, parent=None: calls.append(True)),
    )

    main_window.save_audio()

    assert calls == []


def test_save_audio_shows_error_dialog_on_failure(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
):
    doc = add_document(main_window, "myfile.wav")
    load_signal(doc, np.arange(5000), fs=1000)
    monkeypatch.setattr(
        main_window_module.SaveAudioDialog,
        "get_options",
        staticmethod(
            lambda doc, name, parent=None: SaveOptions(
                path="/tmp/out.wav", target_fs=8000, scale=True
            )
        ),
    )

    class FailingSaveAudio:
        def __init__(self, *args: object):
            pass

        def invoke(self):
            raise RuntimeError("disk full")

    monkeypatch.setattr(main_window_module, "SaveAudio", FailingSaveAudio)
    critical_calls = []
    monkeypatch.setattr(
        main_window_module.QMessageBox,
        "critical",
        staticmethod(lambda *a, **k: critical_calls.append(True)),
    )

    main_window.save_audio()

    assert critical_calls == [True]


def test_show_audio_info_execs_dialog_for_current_document(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
):
    doc = add_document(main_window, "myfile.wav")
    load_signal(doc, np.arange(5000), fs=1000)
    calls = []
    monkeypatch.setattr(
        main_window_module.AudioInfoDialog,
        "show_info",
        staticmethod(lambda doc, name, parent=None: calls.append(name)),
    )

    main_window.show_audio_info()

    assert calls == ["myfile.wav"]


def test_show_audio_info_does_nothing_without_a_current_document(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
):
    calls = []
    monkeypatch.setattr(
        main_window_module.AudioInfoDialog,
        "show_info",
        staticmethod(lambda doc, name, parent=None: calls.append(name)),
    )

    main_window.show_audio_info()

    assert calls == []


# --------------------------- shutdown ---------------------------


def test_quit_app_cleans_up_all_documents_and_quits(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
):
    doc_a = add_document(main_window, "a.wav")
    doc_b = add_document(main_window, "b.wav")
    quit_calls = []
    monkeypatch.setattr(
        QApplication, "quit", staticmethod(lambda: quit_calls.append(True))
    )

    main_window.quit_app()

    assert doc_a.view_model.audio_player.stopped is True
    assert doc_b.view_model.audio_player.stopped is True
    assert quit_calls == [True]


def test_close_event_cleans_up_all_documents_and_accepts(main_window: MainWindow):
    from PyQt6.QtGui import QCloseEvent

    doc = add_document(main_window)
    event = QCloseEvent()

    main_window.closeEvent(event)

    assert doc.view_model.audio_player.stopped is True
    assert event.isAccepted() is True
