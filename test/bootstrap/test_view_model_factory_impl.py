from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot
from support.audio_player import FakeAudioPlayer
from support.job_manager import FakeJobManager

import ui.base.view_model as view_model_module
import ui.document.document_view_model as dvm_module
from bootstrap.view_model_factory_impl import ViewModelFactoryImpl
from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.annotation.tier_search_view_model import TierSearchViewModel
from ui.document.document_view_model import DocumentViewModel
from ui.main.main_view_model import MainViewModel
from ui.spectrogram.spectrogram_view_model import SpectrogramViewModel
from ui.waveform.audio_wave_view_model import AudioWaveViewModel


@pytest.fixture(autouse=True)
def fake_threads(monkeypatch: pytest.MonkeyPatch):
    """Real audio players and thread pools aren't needed to check wiring"""
    monkeypatch.setattr(dvm_module, "AudioPlayer", FakeAudioPlayer)
    monkeypatch.setattr(view_model_module, "JobManager", FakeJobManager)


@pytest.mark.parametrize(
    ("view_model_type", "args"),
    [
        (DocumentViewModel, ()),
        (DocumentViewModel, ("stem", None)),
        (SpectrogramViewModel, ()),
        (AnnotationViewModel, ()),
        (TierSearchViewModel, ()),
        (AudioWaveViewModel, (0,)),
        (MainViewModel, ()),
    ],
)
def test_create_returns_requested_view_model(
    qtbot: QtBot, view_model_type: type, args: tuple
):
    view_model = ViewModelFactoryImpl().create(view_model_type, *args)

    assert isinstance(view_model, view_model_type)


def test_create_raises_for_unknown_view_model_type():
    with pytest.raises(TypeError):
        ViewModelFactoryImpl().create(int)


def test_document_view_model_keeps_file_stem(qtbot: QtBot):
    view_model = ViewModelFactoryImpl().create(DocumentViewModel, "stem", None)

    assert view_model.file_stem == "stem"


def test_tier_search_view_model_searches_project_only_with_dir_path(tmp_path: Path):
    factory = ViewModelFactoryImpl()

    assert not factory.create(TierSearchViewModel).is_project
    assert factory.create(TierSearchViewModel, str(tmp_path)).is_project


def test_use_case_factory_without_dir_path_is_in_memory():
    factory = ViewModelFactoryImpl()

    assert factory.get_use_case_factory(None) is factory.in_mem_use_case_factory


def test_use_case_factory_for_dir_path_is_database_backed_and_cached(tmp_path: Path):
    factory = ViewModelFactoryImpl()

    first = factory.get_use_case_factory(str(tmp_path))

    assert first is not factory.in_mem_use_case_factory
    assert (tmp_path / "phonlab.db").exists()
    assert factory.get_use_case_factory(str(tmp_path)) is first


def test_close_project_closes_the_database_and_forgets_it(tmp_path: Path):
    factory = ViewModelFactoryImpl()
    first = factory.get_use_case_factory(str(tmp_path))
    engine = first.annotation_repository.local_datasource.database.engine
    first.annotation_repository.create_annotation("sample")

    factory.close_project(str(tmp_path))

    reopened = factory.get_use_case_factory(str(tmp_path))
    assert reopened is not first
    assert reopened.annotation_repository.local_datasource.database.engine is not engine
    assert reopened.annotation_repository.find_annotation_by_file_stem("sample")


def test_close_project_ignores_a_directory_that_is_not_open(tmp_path: Path):
    ViewModelFactoryImpl().close_project(str(tmp_path))

    assert not (tmp_path / "phonlab.db").exists()


def test_main_view_model_closes_projects_through_the_factory(
    tmp_path: Path, qtbot: QtBot
):
    factory = ViewModelFactoryImpl()
    view_model = factory.create(MainViewModel)
    view_model.set_dir_path(str(tmp_path))
    first = factory.get_use_case_factory(str(tmp_path))

    view_model.close_project()

    assert view_model.dir_path is None
    assert factory.get_use_case_factory(str(tmp_path)) is not first
