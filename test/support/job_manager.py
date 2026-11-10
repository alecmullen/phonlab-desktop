from PyQt6.QtCore import QObject, pyqtSignal

from ui.base.job import Job


class FakeJobManagerSignals(QObject):
    finished = pyqtSignal()


class FakeJobManager:
    """Records the jobs a view model launches instead of running them on the
    thread pool; a test runs one by calling its `on_success` / `on_error`."""

    def __init__(self):
        self.signals = FakeJobManagerSignals()
        self.jobs: list[Job] = []
        self.queued_jobs: list[Job] = []
        self.quit_called = False

    def __call__(self, job: Job):
        self.jobs.append(job)

    def queue_job(self, job: Job):
        self.queued_jobs.append(job)
        self.jobs.append(job)

    def quit(self):
        self.quit_called = True
