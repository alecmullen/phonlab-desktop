from collections.abc import Generator

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


def test_run_takes_the_job_off_the_queue(qtbot: QtBot):
    worker = make_worker(fake_task([1]), [], [])

    worker.run()

    assert worker.pending == []


def test_run_does_nothing_and_emits_finished_when_no_job_queued(qtbot: QtBot):
    worker = make_worker(fake_task([]), [], [])
    worker.set_job(None)

    with qtbot.waitSignal(worker.signals.finished, timeout=1000):
        worker.run()


def test_run_emits_error_when_task_raises(qtbot: QtBot):
    results = []
    errors = []
    boom = ValueError("boom")
    worker = make_worker(fake_task([1, 2], error=boom), results, errors)

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


def test_set_job_queues_behind_the_pending_job(qtbot: QtBot):
    first = Job(fake_task([1]), lambda r: None, lambda e: None)
    worker = JobWorker(first)
    other_job = Job(fake_task([9]), lambda r: None, lambda e: None)

    worker.set_job(other_job)

    assert worker.pending == [first, other_job]


def test_set_job_with_replace_pending_takes_the_place_of_pending_jobs(
    qtbot: QtBot,
):
    worker = make_worker(fake_task([1]), [], [])
    worker.set_job(Job(fake_task([2]), lambda r: None, lambda e: None))
    latest = Job(fake_task([3]), lambda r: None, lambda e: None, replace_pending=True)

    worker.set_job(latest)

    assert worker.pending == [latest]


def test_set_job_none_drops_pending_jobs(qtbot: QtBot):
    worker = make_worker(fake_task([1]), [], [])

    worker.set_job(None)

    assert worker.pending == []


def test_queue_job_slot_queues_job_on_worker(qtbot: QtBot):
    worker = make_worker(fake_task([1]), [], [])
    new_job = Job(fake_task([2]), lambda r: None, lambda e: None)

    worker.slots.queue_job(new_job)

    assert worker.pending[-1] is new_job


def test_run_runs_queued_jobs_in_order_each_to_its_own_callbacks(qtbot: QtBot):
    seen: dict[str, list[int]] = {"a": [], "b": [], "c": []}
    worker = JobWorker(Job(fake_task([1, 2]), seen["a"].append, lambda e: None))
    worker.set_job(Job(fake_task([3]), seen["b"].append, lambda e: None))
    worker.set_job(Job(fake_task([4, 5]), seen["c"].append, lambda e: None))

    worker.run()

    assert seen == {"a": [1, 2], "b": [3], "c": [4, 5]}


def test_run_sends_an_error_only_to_the_failing_jobs_callback(qtbot: QtBot):
    errors_a: list = []
    errors_b: list = []
    boom = ValueError("boom")
    worker = JobWorker(Job(fake_task([], error=boom), lambda r: None, errors_a.append))
    worker.set_job(Job(fake_task([1]), lambda r: None, errors_b.append))

    worker.run()

    assert errors_a == [boom]
    assert errors_b == []


def test_run_skips_the_jobs_a_replace_pending_job_replaced(qtbot: QtBot):
    ran: list[str] = []
    worker = JobWorker(Job(fake_task([1]), lambda r: ran.append("a"), lambda e: None))
    worker.set_job(Job(fake_task([2]), lambda r: ran.append("b"), lambda e: None))
    worker.set_job(
        Job(
            fake_task([3]),
            lambda r: ran.append("c"),
            lambda e: None,
            replace_pending=True,
        )
    )

    worker.run()

    assert ran == ["c"]


def test_run_stops_without_starting_queued_jobs(qtbot: QtBot):
    ran: list[int] = []
    worker = make_worker(fake_task([1, 2]), ran, [])
    worker.set_job(Job(fake_task([3]), ran.append, lambda e: None))
    worker.should_stop = True

    worker.run()

    assert ran == [1]


def test_stop_slot_sets_should_stop(qtbot: QtBot):
    worker = make_worker(fake_task([1]), [], [])
    assert worker.should_stop is False

    worker.slots.stop()

    assert worker.should_stop is True
