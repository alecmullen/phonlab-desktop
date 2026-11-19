import threading
from collections import deque

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from ui.base.job import Job


class JobWorker(QRunnable):
    """Runs jobs one after another on a pool thread.

    Jobs queued while one runs are kept in order. Each result and error is
    emitted together with the job that produced it, and handed to that job's
    own callbacks only, on the thread that created the worker (the main
    thread). Nothing is connected per job, so a job that is replaced or
    finished never loses results it already emitted."""

    def __init__(self, job: Job):
        super().__init__()
        self.slots = JobWorkerSlots(self)
        self.signals = JobWorkerSignals()
        self._lock = threading.Lock()
        self._pending: deque[Job] = deque([job])
        self.should_stop = False
        # Must be connected on the thread that owns the callbacks (the main
        # thread), so that the delivery is queued onto it:
        self.signals.result.connect(self.slots.deliver_result)
        self.signals.error.connect(self.slots.deliver_error)

    @property
    def pending(self) -> list[Job]:
        """The jobs waiting to run, oldest first"""
        with self._lock:
            return list(self._pending)

    def set_job(self, job: Job | None):
        """Queue `job` behind those already waiting, or in place of them if it
        has `replace_pending`. `None` drops all waiting jobs."""
        with self._lock:
            if job is None or job.replace_pending:
                self._pending.clear()
            if job is not None:
                self._pending.append(job)

    def _next_job(self) -> Job | None:
        with self._lock:
            return self._pending.popleft() if self._pending else None

    def run(self):
        while (job := self._next_job()) is not None:
            try:
                for result in job.task:
                    self.signals.result.emit(job, result)
                    if self.should_stop:
                        job.task.close()
                        self.signals.finished.emit()
                        return
            except Exception as err:  # noqa: BLE001
                self.signals.error.emit(job, err)
        self.signals.finished.emit()


class JobWorkerSignals(QObject):
    result = pyqtSignal(object, object)
    error = pyqtSignal(object, object)
    finished = pyqtSignal()


class JobWorkerSlots(QObject):
    def __init__(self, job_worker: JobWorker):
        super().__init__()
        self.job_worker = job_worker

    @pyqtSlot(object)
    def queue_job(self, job: Job | None):
        self.job_worker.set_job(job)

    @pyqtSlot()
    def stop(self):
        self.job_worker.should_stop = True

    @pyqtSlot(object, object)
    def deliver_result(self, job: Job, result: object):
        job.on_success(result)

    @pyqtSlot(object, object)
    def deliver_error(self, job: Job, error: Exception):
        job.on_error(error)
