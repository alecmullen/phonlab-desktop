from typing import ClassVar

from PyQt6.QtCore import QObject, QThreadPool, QTimer, pyqtSignal

from ui.base.job import Job
from ui.base.job_worker import JobWorker


class JobManager:
    thread_pool: QThreadPool | None = QThreadPool.globalInstance()

    # Workers that are running, or are done but whose results may still be waiting
    # in the GUI thread's event queue. Prevents premature garbage collection
    _live_workers: ClassVar[dict[object, JobWorker]] = {}

    def __init__(self):
        self.signals = JobManagerSignals()

    def __call__(self, job: Job):
        self.worker = JobWorker(job)

        if self.thread_pool is None:
            raise RuntimeError("Thread pool not initialized")

        self.worker.signals.finished.connect(self.signals.finished)

        token = object()
        JobManager._live_workers[token] = self.worker
        self.worker.signals.finished.connect(lambda: JobManager._release(token))

        self.signals.job.connect(self.worker.slots.queue_job)
        self.signals.should_stop.connect(self.worker.slots.stop)

        self.thread_pool.start(self.worker)

    @staticmethod
    def _release(token: object):
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
