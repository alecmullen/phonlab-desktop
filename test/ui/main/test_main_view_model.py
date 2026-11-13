from pathlib import Path

import pytest
from support.annotation_repository import SeedableAnnotationRepository
from support.job_manager import FakeJobManager
from support.mocks import mock_use_case
from support.textgrid import write_simple_textgrid
from support.view_models import make_main_view_model

from core.settings.app_settings import settings
from core.settings.load_display_plan import LoadDisplayPlan
from core.settings.save_display_plan import SaveDisplayPlan
from ui.document.state.plot_layout_state import PlotType
from ui.main.main_view_model import MainViewModel
from ui.main.state.project_import_state import ProjectImportState


def test_dir_path_defaults_to_none():
    assert make_main_view_model().dir_path is None


def test_set_dir_path_stores_path():
    view_model = make_main_view_model()

    view_model.set_dir_path("/some/dir")

    assert view_model.dir_path == "/some/dir"


def test_init_toml_raises_without_dir_path():
    with pytest.raises(ValueError):
        make_main_view_model().init_toml()


def test_init_toml_creates_phonlab_toml_in_dir(tmp_path: Path):
    view_model = make_main_view_model()
    view_model.set_dir_path(str(tmp_path))

    view_model.init_toml()

    assert (tmp_path / "phonlab.toml").is_file()


def test_display_plan_defaults_to_waveform():
    assert make_main_view_model().display_plan == {PlotType.WAVEFORM}


def test_set_display_plan_updates_app_settings():
    view_model = make_main_view_model()

    view_model.set_display_plan({PlotType.ANNOTATION, PlotType.SPECTROGRAM})

    assert settings.display_plan == ["spectrogram", "annotation"]
    assert view_model.display_plan == {PlotType.SPECTROGRAM, PlotType.ANNOTATION}


def test_set_display_plan_is_not_written_anywhere():
    save = mock_use_case(SaveDisplayPlan)
    view_model = make_main_view_model(save_display_plan=save)

    view_model.set_display_plan({PlotType.SPECTROGRAM})

    save.assert_not_called()


def test_opening_project_uses_its_saved_plan():
    load = mock_use_case(LoadDisplayPlan)
    load.return_value = ["annotation"]
    view_model = make_main_view_model(load_display_plan=load)

    view_model.set_dir_path("/some/dir")

    assert load.call_args.args == ("/some/dir",)
    assert view_model.display_plan == {PlotType.ANNOTATION}


def test_opening_project_without_plan_keeps_current_plan():
    view_model = make_main_view_model()  # its load returns None
    view_model.set_display_plan({PlotType.SPECTROGRAM})

    view_model.set_dir_path("/some/dir")

    assert view_model.display_plan == {PlotType.SPECTROGRAM}


def test_closing_project_keeps_current_plan():
    load = mock_use_case(LoadDisplayPlan)
    load.return_value = ["annotation"]
    view_model = make_main_view_model(load_display_plan=load)
    view_model.set_dir_path("/some/dir")

    view_model.set_dir_path(None)

    assert view_model.display_plan == {PlotType.ANNOTATION}


def test_save_window_layout_saves_current_plan_to_project():
    save = mock_use_case(SaveDisplayPlan)
    view_model = make_main_view_model(save_display_plan=save)
    view_model.set_dir_path("/some/dir")
    view_model.set_display_plan({PlotType.WAVEFORM, PlotType.SPECTROGRAM})

    view_model.save_window_layout()

    assert save.call_args.args == (["waveform", "spectrogram"], "/some/dir")


def test_save_window_layout_raises_without_a_project():
    with pytest.raises(ValueError):
        make_main_view_model().save_window_layout()


def run_import_job(view_model: MainViewModel):
    """Runs the recorded import job synchronously, as the worker thread would"""
    job = view_model.job_managers["project_import"].jobs[0]
    for result in job.task:
        job.on_success(result)


def test_is_new_project_until_database_exists(tmp_path: Path):
    view_model = make_main_view_model()
    view_model.set_dir_path(str(tmp_path))
    assert view_model.is_new_project()

    (tmp_path / "phonlab.db").write_bytes(b"")

    assert not view_model.is_new_project()


def test_project_files_pairs_audio_with_textgrid_ignoring_case(tmp_path: Path):
    view_model = make_main_view_model()
    view_model.set_dir_path(str(tmp_path))
    for name in ("a.WAV", "a.textgrid", "b.wav", "notes.txt"):
        (tmp_path / name).write_bytes(b"")

    assert view_model.project_files() == [
        ("a", str(tmp_path / "a.WAV"), str(tmp_path / "a.textgrid")),
        ("b", str(tmp_path / "b.wav"), None),
    ]


def test_project_operations_raise_without_dir_path():
    view_model = make_main_view_model()

    for operation in (
        view_model.is_new_project,
        view_model.project_files,
        view_model.add_project_files,
        view_model.rebuild_project,
    ):
        with pytest.raises(ValueError):
            operation()


def test_add_project_files_registers_stems_and_reports_progress(
    tmp_path: Path, fake_job_manager: type[FakeJobManager]
):
    repository = SeedableAnnotationRepository()
    view_model = make_main_view_model(repository)
    view_model.set_dir_path(str(tmp_path))
    write_simple_textgrid(tmp_path / "a.TextGrid")
    (tmp_path / "a.wav").write_bytes(b"")
    (tmp_path / "b.wav").write_bytes(b"")
    states: list[ProjectImportState] = []
    view_model.subscribe(states.append)

    view_model.add_project_files()
    run_import_job(view_model)

    assert [(s.done, s.total, s.finished) for s in states] == [
        (0, 1, False),
        (1, 1, True),
    ]
    assert states[-1].registered == 2
    assert states[-1].imported == ["a"]
    assert sorted(repository.filenames.values()) == ["a", "b"]


def test_rebuild_project_replaces_database_content(
    tmp_path: Path, fake_job_manager: type[FakeJobManager]
):
    repository = SeedableAnnotationRepository()
    repository.create_annotation("stale")
    view_model = make_main_view_model(repository)
    view_model.set_dir_path(str(tmp_path))
    (tmp_path / "a.wav").write_bytes(b"")
    states: list[ProjectImportState] = []
    view_model.subscribe(states.append)

    view_model.rebuild_project()
    run_import_job(view_model)

    assert states[-1].finished
    assert list(repository.filenames.values()) == ["a"]


def test_import_error_is_reported_as_finished_state(
    tmp_path: Path, fake_job_manager: type[FakeJobManager]
):
    view_model = make_main_view_model()
    view_model.set_dir_path(str(tmp_path))
    states: list[ProjectImportState] = []
    view_model.subscribe(states.append)
    view_model.add_project_files()

    view_model.job_managers["project_import"].jobs[0].on_error(RuntimeError("boom"))

    assert states == [ProjectImportState(finished=True, error="boom")]
