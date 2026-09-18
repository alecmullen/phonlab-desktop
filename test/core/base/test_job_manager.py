from collections.abc import Generator

from pytestqt.qtbot import QtBot

from core.base.job import Job
from core.base.job_manager import JobManager
from core.base.use_case import UseCase


class FakeUseCase(UseCase[int]):
    def __init__(self, values: list[int]):
        self.values = values
        self.stopped = False

    def invoke(self) -> Generator[int, None, None]:
        yield from self.values

    def stop(self) -> None:
        self.stopped = True


def test_call_runs_job_on_thread_pool_and_delivers_results(qtbot: QtBot):
    manager = JobManager()
    results = []
    errors = []
    job = Job(FakeUseCase([1, 2, 3]), results.append, errors.append)

    with qtbot.waitSignal(manager.signals.finished, timeout=2000):
        manager(job)

    assert results == [1, 2, 3]
    assert errors == []


def test_call_creates_a_worker_for_the_job(qtbot: QtBot):
    manager = JobManager()
    job = Job(FakeUseCase([]), lambda r: None, lambda e: None)

    manager(job)

    assert manager.worker.job is None or manager.worker.job is job


def test_queue_job_emits_job_signal(qtbot: QtBot):
    manager = JobManager()
    received = []
    manager.signals.job.connect(received.append)
    job = Job(FakeUseCase([1]), lambda r: None, lambda e: None)

    manager.queue_job(job)

    assert received == [job]


def test_quit_emits_none_job_then_should_stop(qtbot: QtBot):
    manager = JobManager()
    jobs_received = []
    stop_received = []
    manager.signals.job.connect(jobs_received.append)
    manager.signals.should_stop.connect(lambda: stop_received.append(True))

    manager.quit()

    assert jobs_received == [None]
    assert stop_received == [True]


def test_call_wires_job_signal_to_worker_queue(qtbot: QtBot):
    manager = JobManager()
    job1 = Job(FakeUseCase([1]), lambda r: None, lambda e: None)
    manager(job1)
    worker = manager.worker
    job2 = Job(FakeUseCase([2]), lambda r: None, lambda e: None)

    manager.signals.job.emit(job2)

    assert worker.job is job2


def test_call_wires_should_stop_signal_to_worker(qtbot: QtBot):
    manager = JobManager()
    job = Job(FakeUseCase([1]), lambda r: None, lambda e: None)
    manager(job)
    worker = manager.worker

    manager.signals.should_stop.emit()

    assert worker.should_stop is True


def test_call_connects_worker_finished_to_manager_finished(qtbot: QtBot):
    manager = JobManager()
    job = Job(FakeUseCase([]), lambda r: None, lambda e: None)

    manager(job)

    with qtbot.waitSignal(manager.signals.finished, timeout=2000):
        manager.worker.signals.finished.emit()
