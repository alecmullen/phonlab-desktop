import pytest
from support.audio_player import FakeAudioPlayer
from support.job_manager import FakeJobManager
from support.view_models import make_document_view_model

import ui.base.view_model as view_model_module
import ui.document.document_view_model as dvm_module
from ui.document.document_view_model import DocumentViewModel


@pytest.fixture
def fake_job_manager(monkeypatch: pytest.MonkeyPatch) -> type[FakeJobManager]:
    """Launched jobs are recorded on `view_model.job_managers[key].jobs`
    instead of run on the thread pool"""
    monkeypatch.setattr(view_model_module, "JobManager", FakeJobManager)
    return FakeJobManager


@pytest.fixture
def fake_audio_player(monkeypatch: pytest.MonkeyPatch) -> type[FakeAudioPlayer]:
    monkeypatch.setattr(dvm_module, "AudioPlayer", FakeAudioPlayer)
    return FakeAudioPlayer


@pytest.fixture
def document_view_model(
    fake_audio_player: type[FakeAudioPlayer],
    fake_job_manager: type[FakeJobManager],
) -> DocumentViewModel:
    """A document view model with real child view models, whose background
    jobs are recorded rather than run"""
    return make_document_view_model()
