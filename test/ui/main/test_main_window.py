from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
from pytestqt.qtbot import QtBot
from support.annotation_repository import SeedableAnnotationRepository
from support.audio_player import FakeAudioPlayer
from support.job_manager import FakeJobManager
from support.mocks import mock_use_case
from support.textgrid import write_simple_textgrid
from support.view_models import StubViewModelFactory, make_main_view_model

import ui.document.document_view as doc_view_module
import ui.main.main_window as main_window_module
from core.load_audio.entity.audio_signal import AudioSignal
from core.save_audio.save_audio import SaveAudio
from core.settings.app_settings import settings
from ui.document.document_view import DocumentView
from ui.document.document_view_model import DocumentViewModel
from ui.document.state.audio_channel_state import AudioChannelState, AudioState
from ui.document.state.plot_layout_state import PlotType
from ui.main.component.open_audio_dialog import OpenAudioDialog
from ui.main.component.save_audio_dialog import SaveOptions
from ui.main.main_view_model import MainViewModel
from ui.main.main_window import MainWindow
from ui.main.state.audio_open_options import AudioOpenOptionsState


@pytest.fixture(autouse=True)
def disable_zero_crossing_snapping(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cut_and_paste_at_zero_crossings", False)


@pytest.fixture
def save_audio() -> SaveAudio:
    return mock_use_case(SaveAudio)


@pytest.fixture
def project_repository() -> SeedableAnnotationRepository:
    """The project database behind `main_window`"""
    return SeedableAnnotationRepository()


@pytest.fixture
def main_window(
    qtbot: QtBot,
    fake_audio_player: type[FakeAudioPlayer],
    fake_job_manager: type[FakeJobManager],
    save_audio: SaveAudio,
    project_repository: SeedableAnnotationRepository,
) -> MainWindow:
    win = MainWindow(
        StubViewModelFactory(
            {MainViewModel: make_main_view_model(project_repository)},
            save_audio=save_audio,
        )
    )
    qtbot.addWidget(win)
    return win


def add_document(main_window: MainWindow, name: str = "doc.wav") -> DocumentView:
    vm = main_window.view_model_factory.create(DocumentViewModel)
    doc = DocumentView(vm)
    doc.origin_name = name
    doc.origin_path = f"/tmp/{name}"
    main_window.tab_widget.addTab(doc, name)
    main_window.tab_widget.setCurrentIndex(main_window.tab_widget.count() - 1)
    return doc


def load_signal(doc: DocumentView, x: np.ndarray, fs: int):
    doc.view_model.set_audio(
        AudioState({0: AudioChannelState(np.asarray(x, dtype=np.float64), fs)}),
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
        staticmethod(lambda filename, parent=None: AudioOpenOptionsState()),
    )

    main_window.open_files([("sound", str(wav_path), None)], str(tmp_path))

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
        staticmethod(lambda filename, parent=None: AudioOpenOptionsState()),
    )

    main_window.open_files(
        [("sound", str(wav_path), str(textgrid_path))], str(tmp_path)
    )

    doc = main_window.get_current_document()
    annotation_view_model = doc.view_model.annotation_view_model
    job = annotation_view_model.job_managers["parse_textgrid"].jobs[0]
    job.on_success(next(job.task))
    assert {
        node.x for node in annotation_view_model.annotation_state.nodes.values()
    } == {0.0, 1.0}


def stub_overwrite_scenario(
    monkeypatch: pytest.MonkeyPatch,
    has_annotation: bool,
    *answers: QMessageBox.StandardButton,
) -> tuple[list, list]:
    """Every document reports `has_annotation`; returns the (path, overwrite) calls to
    `load_textgrid` and the TextGrid names the user was asked about"""
    loaded: list = []
    asked: list = []
    remaining = list(answers)
    monkeypatch.setattr(
        OpenAudioDialog,
        "get_options",
        staticmethod(lambda filename, parent=None: AudioOpenOptionsState()),
    )
    monkeypatch.setattr(
        DocumentViewModel, "has_annotation", lambda self: has_annotation
    )
    monkeypatch.setattr(
        DocumentView,
        "load_textgrid",
        lambda self, path, overwrite=False: loaded.append((Path(path).name, overwrite)),
    )

    def question(
        parent: object, title: str, text: str, *args: object, **kwargs: object
    ) -> QMessageBox.StandardButton:
        asked.append(text)
        return remaining.pop(0)

    monkeypatch.setattr(QMessageBox, "question", staticmethod(question))
    return loaded, asked


def paired_files(tmp_path: Path, *stems: str) -> list[tuple[str, str, str]]:
    return [
        (stem, str(tmp_path / f"{stem}.wav"), str(tmp_path / f"{stem}.TextGrid"))
        for stem in stems
    ]


def test_open_files_loads_textgrid_without_asking_when_database_is_empty(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    loaded, asked = stub_overwrite_scenario(monkeypatch, False)

    main_window.open_files(paired_files(tmp_path, "a"), str(tmp_path))

    assert loaded == [("a.TextGrid", False)]
    assert asked == []


def test_open_files_overwrites_existing_annotation_when_user_says_yes(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    loaded, asked = stub_overwrite_scenario(
        monkeypatch, True, QMessageBox.StandardButton.Yes
    )

    main_window.open_files(paired_files(tmp_path, "a"), str(tmp_path))

    assert loaded == [("a.TextGrid", True)]
    assert asked == ["Overwrite the existing database with annotation from a.TextGrid?"]


def test_open_files_skips_textgrid_when_user_says_no(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    loaded, asked = stub_overwrite_scenario(
        monkeypatch, True, QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes
    )

    main_window.open_files(paired_files(tmp_path, "a", "b"), str(tmp_path))

    assert loaded == [("b.TextGrid", True)]
    assert len(asked) == 2


def test_open_files_asks_once_and_overwrites_all_on_yes_to_all(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    loaded, asked = stub_overwrite_scenario(
        monkeypatch, True, QMessageBox.StandardButton.YesToAll
    )

    main_window.open_files(paired_files(tmp_path, "a", "b"), str(tmp_path))

    assert loaded == [("a.TextGrid", True), ("b.TextGrid", True)]
    assert len(asked) == 1


def test_open_files_asks_once_and_skips_all_on_no_to_all(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    loaded, asked = stub_overwrite_scenario(
        monkeypatch, True, QMessageBox.StandardButton.NoToAll
    )

    main_window.open_files(paired_files(tmp_path, "a", "b"), str(tmp_path))

    assert loaded == []
    assert len(asked) == 1


def test_open_files_does_nothing_when_dialog_is_cancelled(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    wav_path = tmp_path / "sound.wav"
    wav_path.write_bytes(b"")
    monkeypatch.setattr(
        OpenAudioDialog, "get_options", staticmethod(lambda filename, parent=None: None)
    )

    main_window.open_files([("sound", str(wav_path), None)], str(tmp_path))

    assert main_window.tab_widget.count() == 0


def test_open_single_document_raises_without_a_wav_file(
    main_window: MainWindow, tmp_path: Path
):
    textgrid_path = tmp_path / "only.TextGrid"
    textgrid_path.write_text("")

    with pytest.raises(ValueError):
        main_window.open_single_document([str(textgrid_path)])

    assert main_window.tab_widget.count() == 0


def test_open_files_closes_splash_screen(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    wav_path = tmp_path / "sound.wav"
    wav_path.write_bytes(b"")
    monkeypatch.setattr(
        OpenAudioDialog,
        "get_options",
        staticmethod(lambda filename, parent=None: AudioOpenOptionsState()),
    )
    closed = []
    main_window.splash = type(
        "FakeSplash", (), {"close": lambda self: closed.append(True)}
    )()

    main_window.open_files([("sound", str(wav_path), None)], str(tmp_path))

    assert closed == [True]
    assert main_window.splash is None


def test_save_textgrid_opens_dialog_on_current_document(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
):
    doc = add_document(main_window)
    calls = []
    monkeypatch.setattr(doc, "open_save_textgrid", lambda: calls.append(True))

    main_window.save_textgrid()

    assert calls == [True]


def test_save_textgrid_does_nothing_without_a_document(main_window: MainWindow):
    main_window.save_textgrid()

    assert main_window.tab_widget.count() == 0


# --------------------------- opening projects and documents ---------------------------


@pytest.fixture
def opened(main_window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> list:
    """Records the `open_files` calls instead of creating tabs"""
    calls: list = []
    monkeypatch.setattr(
        main_window,
        "open_files",
        lambda files, dir_path: calls.append((files, dir_path)),
    )
    return calls


def patch_directory_dialog(monkeypatch: pytest.MonkeyPatch, *answers: str):
    remaining = list(answers)
    monkeypatch.setattr(
        QFileDialog,
        "getExistingDirectory",
        staticmethod(lambda *args, **kwargs: remaining.pop(0)),
    )


def patch_file_dialog(monkeypatch: pytest.MonkeyPatch, *selections: list[str]):
    remaining = list(selections)
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileNames",
        staticmethod(lambda *args, **kwargs: (remaining.pop(0), "")),
    )


def test_select_project_does_nothing_when_dialog_is_cancelled(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, opened: list
):
    patch_directory_dialog(monkeypatch, "")

    main_window.select_project_to_open()

    assert opened == []


def run_import_job(main_window: MainWindow):
    """Runs the recorded project import job synchronously, as the worker would"""
    job = main_window.view_model.job_managers["project_import"].jobs[0]
    for result in job.task:
        job.on_success(result)


def make_project(tmp_path: Path, *names: str, database: bool = False) -> Path:
    (tmp_path / "phonlab.toml").write_text("")
    for name in names:
        if name.lower().endswith(".textgrid"):
            write_simple_textgrid(tmp_path / name)
        else:
            (tmp_path / name).write_bytes(b"")
    if database:
        (tmp_path / "phonlab.db").write_bytes(b"")
    return tmp_path


def test_select_project_builds_database_from_textgrids_before_opening_files(
    main_window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    opened: list,
    project_repository: SeedableAnnotationRepository,
):
    make_project(tmp_path, "a.wav", "a.TextGrid", "b.wav")
    patch_directory_dialog(monkeypatch, str(tmp_path))

    main_window.select_project_to_open()

    assert opened == []  # still importing
    run_import_job(main_window)
    [(files, dir_path)] = opened
    assert dir_path == str(tmp_path)
    # Annotations come from the database, so no TextGrid is passed on to be read
    assert sorted(files) == [
        ("a", str(tmp_path / "a.wav"), None),
        ("b", str(tmp_path / "b.wav"), None),
    ]
    assert sorted(project_repository.filenames.values()) == ["a", "b"]
    a = project_repository.find_annotation_by_file_stem("a")
    assert a is not None and [type.type for type in a.types] == ["word"]


def test_select_project_with_existing_database_opens_without_reading_textgrids(
    main_window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    opened: list,
    project_repository: SeedableAnnotationRepository,
):
    make_project(tmp_path, "a.wav", "a.TextGrid", database=True)
    patch_directory_dialog(monkeypatch, str(tmp_path))

    main_window.select_project_to_open()

    assert opened == [([("a", str(tmp_path / "a.wav"), None)], str(tmp_path))]
    assert "project_import" not in main_window.view_model.job_managers
    assert project_repository.filenames == {}


def test_select_project_treats_extensions_case_insensitively(
    main_window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    opened: list,
):
    make_project(
        tmp_path,
        "lower.wav",
        "upper.WAV",
        "mixed.Wav",
        "notes.wav.txt",
        database=True,
    )
    patch_directory_dialog(monkeypatch, str(tmp_path))

    main_window.select_project_to_open()

    [(files, _)] = opened
    assert sorted(stem for stem, _, _ in files) == ["lower", "mixed", "upper"]


def test_select_project_reads_textgrid_with_any_case_suffix_on_first_open(
    main_window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    opened: list,
    project_repository: SeedableAnnotationRepository,
):
    make_project(tmp_path, "a.wav", "a.textgrid")
    patch_directory_dialog(monkeypatch, str(tmp_path))

    main_window.select_project_to_open()
    run_import_job(main_window)

    a = project_repository.find_annotation_by_file_stem("a")
    assert a is not None and len(a.types) == 1


def test_select_project_reports_unreadable_textgrid_and_still_opens(
    main_window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    opened: list,
):
    make_project(tmp_path, "a.wav")
    (tmp_path / "a.TextGrid").write_text("not a textgrid")
    patch_directory_dialog(monkeypatch, str(tmp_path))
    warnings: list[str] = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        staticmethod(lambda parent, title, text, *a: warnings.append(text)),
    )

    main_window.select_project_to_open()
    run_import_job(main_window)

    assert len(warnings) == 1 and "a" in warnings[0]
    assert len(opened) == 1


def test_select_project_does_not_open_files_when_import_fails(
    main_window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    opened: list,
):
    make_project(tmp_path, "a.wav")
    patch_directory_dialog(monkeypatch, str(tmp_path))
    warnings: list[str] = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        staticmethod(lambda parent, title, text, *a: warnings.append(text)),
    )

    main_window.select_project_to_open()
    job = main_window.view_model.job_managers["project_import"].jobs[0]
    job.on_error(RuntimeError("disk full"))

    assert opened == []
    assert len(warnings) == 1 and "disk full" in warnings[0]


def test_select_project_initializes_toml_when_user_agrees(
    main_window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    opened: list,
):
    patch_directory_dialog(monkeypatch, str(tmp_path))
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.Yes),
    )

    main_window.select_project_to_open()
    run_import_job(main_window)

    assert (tmp_path / "phonlab.toml").is_file()
    assert opened == [([], str(tmp_path))]


def test_open_single_document_accepts_uppercase_wav(
    main_window: MainWindow, tmp_path: Path, opened: list
):
    wav = str(tmp_path / "sound.WAV")

    main_window.open_single_document([wav], str(tmp_path))

    assert opened == [([("sound", wav, None)], str(tmp_path))]


def test_select_project_asks_again_when_user_declines_initializing(
    main_window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    opened: list,
):
    patch_directory_dialog(monkeypatch, str(tmp_path), "")
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.No),
    )

    main_window.select_project_to_open()

    assert not (tmp_path / "phonlab.toml").exists()
    assert opened == []


def test_open_single_document_uses_absolute_stem_without_dir(
    main_window: MainWindow, tmp_path: Path, opened: list
):
    wav = str(tmp_path / "sound.wav")

    main_window.open_single_document([wav])

    assert opened == [([(str(tmp_path / "sound"), wav, None)], None)]


def test_open_single_document_uses_relative_stem_within_dir(
    main_window: MainWindow, tmp_path: Path, opened: list
):
    wav = str(tmp_path / "sound.wav")
    textgrid = str(tmp_path / "sound.TextGrid")

    main_window.open_single_document([wav, textgrid], str(tmp_path))

    assert opened == [([("sound", wav, textgrid)], str(tmp_path))]


def test_open_single_document_raises_for_more_than_one_wav(
    main_window: MainWindow, opened: list
):
    with pytest.raises(ValueError):
        main_window.open_single_document(["a.wav", "b.wav"])

    assert opened == []


def test_select_files_does_nothing_when_dialog_is_cancelled(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, opened: list
):
    patch_file_dialog(monkeypatch, [])

    main_window.select_files_to_open()

    assert opened == []


def test_select_files_opens_selected_document(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, opened: list
):
    patch_file_dialog(monkeypatch, ["/data/sound.wav"])

    main_window.select_files_to_open()

    assert opened == [([("/data/sound", "/data/sound.wav", None)], None)]


def test_select_files_reports_invalid_selection_and_asks_again(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, opened: list
):
    patch_file_dialog(monkeypatch, ["only.TextGrid"], [])
    messages: list = []
    monkeypatch.setattr(
        QMessageBox,
        "information",
        staticmethod(lambda *args, **kwargs: messages.append(args)),
    )

    main_window.select_files_to_open()

    assert len(messages) == 1
    assert opened == []


def test_select_new_tab_files_starts_in_current_project_dir(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
):
    main_window.view_model.set_dir_path("/project")
    directories: list = []
    monkeypatch.setattr(
        main_window,
        "select_files_to_open",
        lambda dir=None: directories.append(dir),
    )

    main_window.select_new_tab_files()

    assert directories == ["/project"]


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
    assert len(main_window.clipboard.channels[0].x) == 1000


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


# --------------------------- display plan ---------------------------


def test_switching_tabs_applies_the_current_display_plan(main_window: MainWindow):
    first = add_document(main_window, "first.wav")
    add_document(main_window, "second.wav")  # the current tab
    main_window.view_model.set_display_plan({PlotType.WAVEFORM, PlotType.SPECTROGRAM})

    main_window.tab_widget.setCurrentWidget(first)

    assert PlotType.SPECTROGRAM in first.view_model.plot_layout_state.plots


def test_toggling_a_plot_updates_the_display_plan(main_window: MainWindow):
    doc = add_document(main_window)
    doc.view_model.set_audio(
        AudioState({0: AudioChannelState(np.zeros(2000), 1000)}),
        primary_channel_idx=0,
        reset_window=True,
    )
    doc.view_model.update_spectrogram = lambda: None

    main_window.plot_wave_sgram()

    assert settings.display_plan == ["waveform", "spectrogram"]


def test_save_layout_action_needs_a_project(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    assert main_window.save_layout_action.isEnabled() is False
    wav_path = tmp_path / "sound.wav"
    wav_path.write_bytes(b"")
    monkeypatch.setattr(
        OpenAudioDialog,
        "get_options",
        staticmethod(lambda filename, parent=None: AudioOpenOptionsState()),
    )

    main_window.open_files([("sound", str(wav_path), None)], str(tmp_path))

    assert main_window.save_layout_action.isEnabled() is True


def test_save_window_layout_saves_the_plan_to_the_project(main_window: MainWindow):
    save = main_window.view_model.save_display_plan_use_case
    main_window.view_model.set_dir_path("/some/dir")
    main_window.view_model.set_display_plan({PlotType.WAVEFORM, PlotType.SPECTROGRAM})

    main_window.save_window_layout()

    assert save.call_args.args == (["waveform", "spectrogram"], "/some/dir")


def test_save_window_layout_reports_a_failed_save(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
):
    main_window.view_model.set_dir_path("/some/dir")
    main_window.view_model.save_display_plan_use_case.side_effect = OSError("denied")
    errors = []
    monkeypatch.setattr(
        QMessageBox, "critical", staticmethod(lambda *args: errors.append(args))
    )

    main_window.save_window_layout()

    assert len(errors) == 1


def test_a_new_document_starts_with_the_display_plan(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    wav_path = tmp_path / "sound.wav"
    wav_path.write_bytes(b"")
    monkeypatch.setattr(
        OpenAudioDialog,
        "get_options",
        staticmethod(lambda filename, parent=None: AudioOpenOptionsState()),
    )
    main_window.view_model.set_display_plan({PlotType.WAVEFORM, PlotType.ANNOTATION})

    main_window.open_files([("sound", str(wav_path), None)], None)

    doc = main_window.get_current_document()
    assert doc.view_model.plot_layout_state.plots == {
        PlotType.WAVEFORM,
        PlotType.ANNOTATION,
    }


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


def test_paste_special_forwards_clipboard_to_document(main_window: MainWindow):
    doc = add_document(main_window)
    calls = []
    doc.paste_special = lambda clip: calls.append(clip)
    main_window.clipboard = AudioSignal(np.array([1.0, 2.0]), 1000)

    main_window.paste_special()

    assert len(calls) == 1
    assert calls[0] is main_window.clipboard


def test_paste_special_does_nothing_without_a_clipboard(main_window: MainWindow):
    doc = add_document(main_window)
    calls = []
    doc.paste_special = lambda clip: calls.append(clip)

    main_window.paste_special()

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
    main_window: MainWindow, save_audio: SaveAudio, monkeypatch: pytest.MonkeyPatch
):
    doc = add_document(main_window, "myfile.wav")
    load_signal(doc, np.arange(5000), fs=1000)
    monkeypatch.setattr(
        main_window_module.SaveAudioDialog,
        "get_options",
        staticmethod(
            lambda doc, name, parent=None: SaveOptions(
                path="/tmp/out.wav", target_fs=8000, scale=True, channels=[0]
            )
        ),
    )

    main_window.save_audio()

    save_audio.assert_called_once()
    path, channels, target_fs, scale = save_audio.call_args.args
    assert (path, channels[0].fs, target_fs, scale) == (
        "/tmp/out.wav",
        1000,
        8000,
        True,
    )


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
    main_window: MainWindow, save_audio: SaveAudio, monkeypatch: pytest.MonkeyPatch
):
    doc = add_document(main_window, "myfile.wav")
    load_signal(doc, np.arange(5000), fs=1000)
    monkeypatch.setattr(
        main_window_module.SaveAudioDialog,
        "get_options",
        staticmethod(
            lambda doc, name, parent=None: SaveOptions(
                path="/tmp/out.wav", target_fs=8000, scale=True, channels=[0]
            )
        ),
    )

    save_audio.side_effect = RuntimeError("disk full")
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
        doc_view_module.AudioInfoDialog,
        "show_info",
        staticmethod(
            lambda primary_channel, stereo_channels, name, parent=None: calls.append(
                name
            )
        ),
    )

    main_window.show_audio_info()

    assert calls == ["myfile.wav"]


def test_show_audio_info_does_nothing_without_a_current_document(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch
):
    calls = []
    monkeypatch.setattr(
        doc_view_module.AudioInfoDialog,
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


# --------------------------- spectrogram only for the shown tab ---------------------------


def test_only_the_current_tab_is_shown(main_window: MainWindow):
    first = add_document(main_window, "one.wav")
    second = add_document(main_window, "two.wav")
    third = add_document(main_window, "three.wav")

    assert [d.view_model.is_shown for d in (first, second, third)] == [
        False,
        False,
        True,
    ]


def test_switching_tabs_changes_which_document_is_shown(main_window: MainWindow):
    first = add_document(main_window, "one.wav")
    second = add_document(main_window, "two.wav")

    main_window.tab_widget.setCurrentIndex(0)

    assert first.view_model.is_shown
    assert not second.view_model.is_shown


def test_closing_the_current_tab_shows_the_one_that_becomes_current(
    main_window: MainWindow,
):
    first = add_document(main_window, "one.wav")
    add_document(main_window, "two.wav")
    assert not first.view_model.is_shown

    main_window.close_current_tab()

    assert main_window.tab_widget.count() == 1
    assert first.view_model.is_shown


def test_clip_tab_opens_hidden_behind_its_source(main_window: MainWindow):
    source = add_document(main_window, "source.wav")
    load_signal(source, np.arange(10000), fs=1000)
    source.view_model.start_selection(2.0)
    source.view_model.continue_selection(3.0)

    main_window.copy_selection()

    assert main_window.tab_widget.count() == 2
    clip = main_window.tab_widget.widget(1)
    assert isinstance(clip, DocumentView)
    assert not clip.view_model.is_shown
    assert source.view_model.is_shown


# --------------------------- project menu ---------------------------


def test_project_actions_are_disabled_until_a_project_is_open(
    main_window: MainWindow, tmp_path: Path
):
    assert not main_window.add_files_action.isEnabled()
    assert not main_window.rebuild_action.isEnabled()

    main_window.view_model.set_dir_path(str(tmp_path))
    main_window.update_project_actions()

    assert main_window.add_files_action.isEnabled()
    assert main_window.rebuild_action.isEnabled()


def test_menus_are_ordered_file_edit_project_view(main_window: MainWindow):
    titles = [
        action.text().replace("&", "") for action in main_window.menuBar().actions()
    ]

    assert titles == ["File", "Edit", "Project", "View"]


def test_project_menu_lists_the_project_actions(main_window: MainWindow):
    menu = next(
        action.menu()
        for action in main_window.menuBar().actions()
        if action.text().replace("&", "") == "Project"
    )

    assert menu.actions() == [main_window.add_files_action, main_window.rebuild_action]


def capture_information(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    messages: list[str] = []
    monkeypatch.setattr(
        QMessageBox,
        "information",
        staticmethod(lambda parent, title, text, *a: messages.append(text)),
    )
    return messages


def test_add_new_files_registers_new_stems_and_reads_textgrids_for_empty_ones(
    main_window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    project_repository: SeedableAnnotationRepository,
):
    make_project(tmp_path, "old.wav", "new.wav", "new.TextGrid", "old.TextGrid")
    project_repository.create_annotation("old")  # in the database, but empty
    main_window.view_model.set_dir_path(str(tmp_path))
    messages = capture_information(monkeypatch)

    main_window.add_new_files()
    run_import_job(main_window)

    assert sorted(project_repository.filenames.values()) == ["new", "old"]
    for stem in ("new", "old"):
        annotation = project_repository.find_annotation_by_file_stem(stem)
        assert annotation is not None and len(annotation.types) == 1
    assert messages == ["Added 1 new files and read 2 TextGrids."]


def test_add_new_files_leaves_existing_annotations_alone(
    main_window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    project_repository: SeedableAnnotationRepository,
):
    make_project(tmp_path, "a.wav", "a.TextGrid")
    main_window.view_model.set_dir_path(str(tmp_path))
    capture_information(monkeypatch)
    main_window.add_new_files()
    run_import_job(main_window)
    before = project_repository.find_annotation_by_file_stem("a")
    main_window.view_model.job_managers.clear()

    main_window.add_new_files()
    run_import_job(main_window)

    assert project_repository.find_annotation_by_file_stem("a") == before


def test_add_new_files_reloads_annotations_of_open_documents(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    make_project(tmp_path, "a.wav")
    main_window.view_model.set_dir_path(str(tmp_path))
    capture_information(monkeypatch)
    reloaded: list[DocumentViewModel] = []
    monkeypatch.setattr(
        DocumentViewModel, "reload_annotation", lambda self: reloaded.append(self)
    )
    first, second = add_document(main_window), add_document(main_window, "two.wav")

    main_window.add_new_files()
    run_import_job(main_window)

    assert reloaded == [first.view_model, second.view_model]


def test_add_new_files_reports_unreadable_textgrids(
    main_window: MainWindow, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    make_project(tmp_path, "a.wav")
    (tmp_path / "a.TextGrid").write_text("not a textgrid")
    main_window.view_model.set_dir_path(str(tmp_path))
    messages = capture_information(monkeypatch)

    main_window.add_new_files()
    run_import_job(main_window)

    [message] = messages
    assert "Could not read the TextGrid for: a" in message


def test_rebuild_project_does_nothing_when_user_declines(
    main_window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    project_repository: SeedableAnnotationRepository,
):
    make_project(tmp_path, "a.wav")
    project_repository.create_annotation("stale")
    main_window.view_model.set_dir_path(str(tmp_path))
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *args, **kwargs: QMessageBox.StandardButton.No),
    )

    main_window.rebuild_project()

    assert "project_import" not in main_window.view_model.job_managers
    assert list(project_repository.filenames.values()) == ["stale"]


def test_rebuild_project_rereads_textgrids_into_a_new_database(
    main_window: MainWindow,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    project_repository: SeedableAnnotationRepository,
):
    make_project(tmp_path, "a.wav", "a.TextGrid")
    project_repository.create_annotation("stale")
    main_window.view_model.set_dir_path(str(tmp_path))
    questions: list[str] = []

    def question(
        parent: object, title: str, text: str, *args: object
    ) -> QMessageBox.StandardButton:
        questions.append(text)
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", staticmethod(question))
    messages = capture_information(monkeypatch)
    reloaded: list[DocumentViewModel] = []
    monkeypatch.setattr(
        DocumentViewModel, "reload_annotation", lambda self: reloaded.append(self)
    )
    doc = add_document(main_window)

    main_window.rebuild_project()
    run_import_job(main_window)

    assert str(tmp_path) in questions[0]
    assert list(project_repository.filenames.values()) == ["a"]
    assert messages == ["Rebuilt the project database from 1 TextGrids."]
    assert reloaded == [doc.view_model]


def test_open_single_document_accepts_textgrid_with_any_case_suffix(
    main_window: MainWindow, tmp_path: Path, opened: list
):
    wav, textgrid = str(tmp_path / "a.wav"), str(tmp_path / "a.textgrid")

    main_window.open_single_document([wav, textgrid], str(tmp_path))

    assert opened == [([("a", wav, textgrid)], str(tmp_path))]
