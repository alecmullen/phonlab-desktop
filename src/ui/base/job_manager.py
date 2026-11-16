from typing import ClassVar

from PyQt6.QtCore import QObject, QThreadPool, QTimer, pyqtSignal

from ui.base.job import Job
from ui.base.job_worker import JobWorker


class JobManager:
    thread_pool: QThreadPool | None = QThreadPool.globalInstance()

    # Workers that are running, or are done but whose results may still be waiting
    # in the GUI thread's event queue. A worker owns the connections that deliver
    # those results, so it must not be destroyed before they arrive. Its manager
    # does not keep it that long: a manager can be dropped (ViewModel.close_thread)
    # while the job still runs, and a worker nobody refers to is garbage collected
    # at the next collection, at any moment. A result delivered to a slot that
    # collection has just destroyed calls freed memory (a segmentation fault).
    _live_workers: ClassVar[dict[object, JobWorker]] = {}

    def __init__(self):
        self.signals = JobManagerSignals()

    def __call__(self, job: Job):
        self.worker = JobWorker(job)

        if self.thread_pool is None:
            raise RuntimeError("Thread pool not initialized")

        # Connect before starting: a fast job can finish (and emit
        # `finished`) before start() returns, and that emit would be lost.
        self.worker.signals.finished.connect(self.signals.finished)

        # `finished` is the last thing a worker emits, so once it arrives (on the
        # GUI thread) every result has been delivered. The token, not the worker,
        # is what the connection refers to, or the connection would keep it alive.
        token = object()
        JobManager._live_workers[token] = self.worker
        self.worker.signals.finished.connect(lambda: JobManager._release(token))

        self.signals.job.connect(self.worker.slots.queue_job)
        self.signals.should_stop.connect(self.worker.slots.stop)

        self.thread_pool.start(self.worker)

    @staticmethod
    def _release(token: object):
        # Not from inside the slot of the worker's own signal: let go once that
        # has returned
        QTimer.singleShot(0, lambda: JobManager._live_workers.pop(token, None))

    def queue_job(self, job: Job):
        self.signals.job.emit(job)

    def quit(self):
        self.signals.job.emit(None)
        self.signals.should_stop.emit()


class JobManagerSignals(QObject):
    job = pyqtSignal(object)
    should_stop = pyqtSignal()
    finished = pyqtSignal()
