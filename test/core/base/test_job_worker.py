from collections.abc import Generator

import pytest
from pytestqt.qtbot import QtBot

from core.base.job import Job
from core.base.job_worker import JobWorker
from core.base.use_case import UseCase


class FakeUseCase(UseCase[int]):
    def __init__(self, values: list[int], error: Exception | None = None):
        self.values = values
        self.error = error
        self.stop_requested_at: int | None = None
        self.stopped = False

    def invoke(self) -> Generator[int, None, None]:
        yield from self.values
        if self.error is not None:
            raise self.error

    def stop(self) -> None:
        self.stopped = True


def make_worker(use_case: UseCase, results: list, errors: list) -> JobWorker:
    job = Job(use_case, results.append, errors.append)
    return JobWorker(job)


def test_run_emits_result_for_each_yielded_value(qtbot: QtBot):
    results = []
    errors = []
    worker = make_worker(FakeUseCase([1, 2, 3]), results, errors)

    worker.run()

    assert results == [1, 2, 3]
    assert errors == []


def test_run_emits_finished_after_use_case_completes(qtbot: QtBot):
    results = []
    worker = make_worker(FakeUseCase([1]), results, [])

    with qtbot.waitSignal(worker.signals.finished, timeout=1000):
        worker.run()


def test_run_clears_job_after_starting_it(qtbot: QtBot):
    worker = make_worker(FakeUseCase([1]), [], [])

    worker.run()

    assert worker.job is None


def test_run_does_nothing_and_emits_finished_when_no_job_queued(qtbot: QtBot):
    worker = make_worker(FakeUseCase([]), [], [])
    worker.job = None

    with qtbot.waitSignal(worker.signals.finished, timeout=1000):
        worker.run()


def test_run_emits_error_and_reraises_when_use_case_raises(qtbot: QtBot):
    results = []
    errors = []
    boom = ValueError("boom")
    worker = make_worker(FakeUseCase([1, 2], error=boom), results, errors)

    with pytest.raises(ValueError):
        worker.run()

    assert results == [1, 2]
    assert errors == [boom]


def test_run_stops_use_case_and_emits_finished_when_should_stop_is_set(
    qtbot: QtBot,
):
    use_case = FakeUseCase([1, 2, 3])
    results = []
    worker = make_worker(use_case, results, [])
    worker.should_stop = True

    with qtbot.waitSignal(worker.signals.finished, timeout=1000):
        worker.run()

    assert results == [1]
    assert use_case.stopped is True


def test_set_job_replaces_pending_job(qtbot: QtBot):
    worker = make_worker(FakeUseCase([1]), [], [])
    other_results = []
    other_job = Job(FakeUseCase([9]), other_results.append, lambda e: None)

    worker.set_job(other_job)

    assert worker.job is other_job


def test_queue_job_slot_sets_job_on_worker(qtbot: QtBot):
    worker = make_worker(FakeUseCase([1]), [], [])
    new_job = Job(FakeUseCase([2]), lambda r: None, lambda e: None)

    worker.slots.queue_job(new_job)

    assert worker.job is new_job


def test_stop_slot_sets_should_stop(qtbot: QtBot):
    worker = make_worker(FakeUseCase([1]), [], [])
    assert worker.should_stop is False

    worker.slots.stop()

    assert worker.should_stop is True
