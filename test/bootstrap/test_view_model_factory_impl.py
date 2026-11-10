from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot
from support.audio_player import FakeAudioPlayer
from support.job_manager import FakeJobManager

import ui.base.view_model as view_model_module
import ui.document.document_view_model as dvm_module
from bootstrap.view_model_factory_impl import ViewModelFactoryImpl
from ui.annotation.annotation_view_model import AnnotationViewModel
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


def test_use_case_factory_without_dir_path_is_in_memory():
    factory = ViewModelFactoryImpl()

    assert factory.get_use_case_factory(None) is factory.in_mem_use_case_factory


def test_use_case_factory_for_dir_path_is_database_backed_and_cached(tmp_path: Path):
    factory = ViewModelFactoryImpl()

    first = factory.get_use_case_factory(str(tmp_path))

    assert first is not factory.in_mem_use_case_factory
    assert (tmp_path / "phonlab.db").exists()
    assert factory.get_use_case_factory(str(tmp_path)) is first
