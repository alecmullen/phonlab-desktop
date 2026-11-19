import gc
import threading
import time
import weakref
from collections.abc import Generator

from PyQt6.QtCore import QCoreApplication, QThreadPool
from pytestqt.qtbot import QtBot

from ui.base.job import Job
from ui.base.job_manager import JobManager
from ui.base.view_model import ViewModel


def fake_task(values: list[int]) -> Generator[int, None, None]:
    yield from values


def test_call_runs_job_on_thread_pool_and_delivers_results(qtbot: QtBot):
    manager = JobManager()
    results = []
    errors = []
    job = Job(fake_task([1, 2, 3]), results.append, errors.append)

    with qtbot.waitSignal(manager.signals.finished, timeout=2000):
        manager(job)

    assert results == [1, 2, 3]
    assert errors == []


def test_call_creates_a_worker_for_the_job(qtbot: QtBot):
    manager = JobManager()
    job = Job(fake_task([]), lambda r: None, lambda e: None)

    manager(job)

    assert manager.worker.job is None or manager.worker.job is job


def test_queue_job_emits_job_signal(qtbot: QtBot):
    manager = JobManager()
    received = []
    manager.signals.job.connect(received.append)
    job = Job(fake_task([1]), lambda r: None, lambda e: None)

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
    job1 = Job(fake_task([1]), lambda r: None, lambda e: None)
    manager(job1)
    worker = manager.worker
    job2 = Job(fake_task([2]), lambda r: None, lambda e: None)

    manager.signals.job.emit(job2)

    assert worker.job is job2


def test_call_wires_should_stop_signal_to_worker(qtbot: QtBot):
    manager = JobManager()
    job = Job(fake_task([1]), lambda r: None, lambda e: None)
    manager(job)
    worker = manager.worker

    manager.signals.should_stop.emit()

    assert worker.should_stop is True


def test_call_connects_worker_finished_to_manager_finished(qtbot: QtBot):
    manager = JobManager()
    job = Job(fake_task([]), lambda r: None, lambda e: None)

    manager(job)

    with qtbot.waitSignal(manager.signals.finished, timeout=2000):
        manager.worker.signals.finished.emit()


def test_finished_is_emitted_for_every_instant_job(qtbot: QtBot):
    # `finished` must be wired up before the worker starts, or a job that
    # completes immediately emits it with nobody listening.
    for _ in range(30):
        manager = JobManager()
        job = Job(fake_task([]), lambda r: None, lambda e: None)

        with qtbot.waitSignal(manager.signals.finished, timeout=2000):
            manager(job)


def test_callbacks_run_on_the_main_thread(qtbot: QtBot):
    # A callback that launches another job must not run on the worker
    # thread, or the new job's manager never gets its finished signal.
    manager = JobManager()
    threads = []
    job = Job(
        fake_task([1]),
        lambda r: threads.append(threading.current_thread()),
        lambda e: None,
    )

    with qtbot.waitSignal(manager.signals.finished, timeout=2000):
        manager(job)
    qtbot.waitUntil(lambda: len(threads) == 1, timeout=2000)

    assert threads[0] is threading.main_thread()


def test_result_of_a_dropped_job_still_arrives_after_gc_ran(qtbot: QtBot):
    """The garbage collector frees a worker nothing refers to any more, along with the
    slots that receive its results. Results it emitted are still waiting in the event
    queue then, and calling a slot that has been freed is a segmentation fault (or
    the result is lost)."""
    results: list[int] = []
    started = threading.Event()
    proceed = threading.Event()

    def slow_task() -> Generator[int, None, None]:
        started.set()
        proceed.wait(5)
        yield 1

    def on_success(result: int):
        results.append(result)

    view_model = ViewModel()
    view_model.launch_task("task", slow_task(), on_success, lambda e: None)
    assert started.wait(5)
    view_model.close_thread("task")  # drops the manager while the job still runs
    on_success_ref = weakref.ref(on_success)
    del on_success

    proceed.set()
    assert QThreadPool.globalInstance().waitForDone(5000)
    time.sleep(0.1)  # the pool lets go of the finished worker
    gc.collect()
    assert on_success_ref() is not None  # the result still has to be delivered
    QCoreApplication.processEvents()

    assert results == [1]
