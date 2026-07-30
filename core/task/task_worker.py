from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot

from core.task.job import Job


class TaskWorker(QRunnable):

    def __init__(self, job: Job):
        super().__init__()
        self.slots = TaskWorkerSlots(self)
        self.signals = TaskWorkerSignals()
        self.job = job

    def set_job(self, job: Job):
        self.job = job

    def run(self):
        while True:
            if self.job is not None:
                job = self.job
                self.job = None

                self.signals.result.connect(job.on_success)
                self.signals.error.connect(job.on_error)
                try:
                    result = job.task()
                    self.signals.result.emit(result)
                except Exception as err:
                    self.signals.error.emit(err)
                    raise
            if self.job is None:
                self.signals.finished.emit()
                break

class TaskWorkerSignals(QObject):
    result = pyqtSignal(object)
    error = pyqtSignal(Exception)
    finished = pyqtSignal()

class TaskWorkerSlots(QObject):
    def __init__(self, task_worker: TaskWorker):
        super().__init__()
        self.task_worker = task_worker

    @pyqtSlot(object)
    def queue_job(self, job: Job):
        self.task_worker.set_job(job)
        
class TaskManager:
    
    thread_pool = QThreadPool()

    def __init__(self):
        self.signals = TaskManagerSignals()

    def __call__(self, job: Job):
        self.worker = TaskWorker(job)
        self.thread_pool.start(self.worker)

        self.worker.signals.finished.connect(self.signals.finished)

        self.signals.job.connect(self.worker.slots.queue_job)

    def queue_job(self, job: Job):
        self.signals.job.emit(job)

    def quit(self):
        self.signals.job.emit(None)

class TaskManagerSignals(QObject):
    job = pyqtSignal(object)
    finished = pyqtSignal()
