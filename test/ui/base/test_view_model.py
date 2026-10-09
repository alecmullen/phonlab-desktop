import pytest
from PyQt6.QtCore import QObject, pyqtSignal
from pytestqt.qtbot import QtBot

import ui.base.view_model as view_model_module
from core.base.job import Job
from ui.base.view_model import ViewModel


class FakeJobManagerSignals(QObject):
    finished = pyqtSignal()


class FakeJobManager:
    def __init__(self):
        self.signals = FakeJobManagerSignals()
        self.jobs: list[Job] = []
        self.queued_jobs: list[Job] = []
        self.quit_called = False

    def __call__(self, job: Job):
        self.jobs.append(job)

    def queue_job(self, job: Job):
        self.queued_jobs.append(job)

    def quit(self):
        self.quit_called = True


class DummyUseCase:
    pass


def noop(*args: object) -> None:
    pass


@pytest.fixture
def fake_job_manager(monkeypatch: pytest.MonkeyPatch) -> type[FakeJobManager]:
    monkeypatch.setattr(view_model_module, "JobManager", FakeJobManager)
    return FakeJobManager


def test_subscribe_connects_slot_to_state_changed(qtbot: QtBot):
    view_model = ViewModel()
    received = []
    view_model.subscribe(received.append)

    view_model.state_changed.emit("new state")

    assert received == ["new state"]


def test_launch_use_case_creates_job_manager_for_new_key(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = ViewModel()
    use_case = DummyUseCase()

    view_model.launch_use_case("key1", use_case, noop, noop)

    assert set(view_model.job_managers.keys()) == {"key1"}
    manager = view_model.job_managers["key1"]
    assert isinstance(manager, fake_job_manager)
    assert len(manager.jobs) == 1
    assert manager.jobs[0].use_case is use_case


def test_launch_use_case_queues_job_on_existing_manager(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = ViewModel()
    view_model.launch_use_case("key1", DummyUseCase(), noop, noop)
    manager = view_model.job_managers["key1"]

    view_model.launch_use_case("key1", DummyUseCase(), noop, noop)

    assert view_model.job_managers["key1"] is manager
    assert len(manager.jobs) == 1
    assert len(manager.queued_jobs) == 1


def test_launch_use_case_only_once_skips_queueing_on_existing_manager(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = ViewModel()
    view_model.launch_use_case("key1", DummyUseCase(), noop, noop)
    manager = view_model.job_managers["key1"]

    view_model.launch_use_case("key1", DummyUseCase(), noop, noop, only_once=True)

    assert manager.queued_jobs == []


def test_launch_use_case_only_once_still_launches_for_new_key(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = ViewModel()

    view_model.launch_use_case("key1", DummyUseCase(), noop, noop, only_once=True)

    assert "key1" in view_model.job_managers
    assert len(view_model.job_managers["key1"].jobs) == 1


def test_manager_removed_from_job_managers_when_finished(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = ViewModel()
    view_model.launch_use_case("key1", DummyUseCase(), noop, noop)
    manager = view_model.job_managers["key1"]

    manager.signals.finished.emit()

    assert "key1" not in view_model.job_managers


def test_manager_not_removed_if_replaced_before_finishing(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = ViewModel()
    view_model.launch_use_case("key1", DummyUseCase(), noop, noop)
    original_manager = view_model.job_managers["key1"]

    replacement_manager = fake_job_manager()
    view_model.job_managers["key1"] = replacement_manager

    original_manager.signals.finished.emit()

    assert view_model.job_managers["key1"] is replacement_manager


def test_close_threads_quits_all_managers(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = ViewModel()
    view_model.launch_use_case("key1", DummyUseCase(), noop, noop)
    view_model.launch_use_case("key2", DummyUseCase(), noop, noop)
    managers = list(view_model.job_managers.values())

    view_model.close_threads()

    assert all(manager.quit_called for manager in managers)


def test_close_thread_quits_and_removes_specific_manager(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = ViewModel()
    view_model.launch_use_case("key1", DummyUseCase(), noop, noop)
    manager = view_model.job_managers["key1"]

    view_model.close_thread("key1")

    assert manager.quit_called is True
    assert "key1" not in view_model.job_managers


def test_close_thread_for_missing_key_is_a_noop(qtbot: QtBot):
    view_model = ViewModel()

    view_model.close_thread("missing")

    assert view_model.job_managers == {}
