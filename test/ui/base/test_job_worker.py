from collections.abc import Generator

import pytest
from pytestqt.qtbot import QtBot

from ui.base.job import Job
from ui.base.job_worker import JobWorker


def fake_task(
    values: list[int],
    error: Exception | None = None,
    closed: list[bool] | None = None,
) -> Generator[int, None, None]:
    try:
        yield from values
        if error is not None:
            raise error
    except GeneratorExit:
        if closed is not None:
            closed.append(True)
        raise


def make_worker(task: Generator, results: list, errors: list) -> JobWorker:
    return JobWorker(Job(task, results.append, errors.append))


def test_run_emits_result_for_each_yielded_value(qtbot: QtBot):
    results = []
    errors = []
    worker = make_worker(fake_task([1, 2, 3]), results, errors)

    worker.run()

    assert results == [1, 2, 3]
    assert errors == []


def test_run_emits_finished_after_task_completes(qtbot: QtBot):
    results = []
    worker = make_worker(fake_task([1]), results, [])

    with qtbot.waitSignal(worker.signals.finished, timeout=1000):
        worker.run()


def test_run_clears_job_after_starting_it(qtbot: QtBot):
    worker = make_worker(fake_task([1]), [], [])

    worker.run()

    assert worker.job is None


def test_run_does_nothing_and_emits_finished_when_no_job_queued(qtbot: QtBot):
    worker = make_worker(fake_task([]), [], [])
    worker.job = None

    with qtbot.waitSignal(worker.signals.finished, timeout=1000):
        worker.run()


def test_run_emits_error_and_reraises_when_task_raises(qtbot: QtBot):
    results = []
    errors = []
    boom = ValueError("boom")
    worker = make_worker(fake_task([1, 2], error=boom), results, errors)

    with pytest.raises(ValueError):
        worker.run()

    assert results == [1, 2]
    assert errors == [boom]


def test_run_closes_task_and_emits_finished_when_should_stop_is_set(
    qtbot: QtBot,
):
    closed = []
    results = []
    worker = make_worker(fake_task([1, 2, 3], closed=closed), results, [])
    worker.should_stop = True

    with qtbot.waitSignal(worker.signals.finished, timeout=1000):
        worker.run()

    assert results == [1]
    assert closed == [True]


def test_set_job_replaces_pending_job(qtbot: QtBot):
    worker = make_worker(fake_task([1]), [], [])
    other_results = []
    other_job = Job(fake_task([9]), other_results.append, lambda e: None)

    worker.set_job(other_job)

    assert worker.job is other_job


def test_queue_job_slot_sets_job_on_worker(qtbot: QtBot):
    worker = make_worker(fake_task([1]), [], [])
    new_job = Job(fake_task([2]), lambda r: None, lambda e: None)

    worker.slots.queue_job(new_job)

    assert worker.job is new_job


def test_stop_slot_sets_should_stop(qtbot: QtBot):
    worker = make_worker(fake_task([1]), [], [])
    assert worker.should_stop is False

    worker.slots.stop()

    assert worker.should_stop is True
