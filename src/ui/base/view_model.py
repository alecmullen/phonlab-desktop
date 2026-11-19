from collections.abc import Callable, Generator

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from ui.base.job import Job
from ui.base.job_manager import JobManager


class ViewModel(QObject):
    state_changed = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.job_managers: dict[str, JobManager] = {}

    def subscribe(self, slot: Callable):
        self.state_changed.connect(slot)

    def launch_task[T](
        self,
        key: str,
        task: Generator[T, None, None],
        on_success: Callable,
        on_error: Callable,
        only_once: bool = False,
        on_finished: Callable | None = None,
        replace_pending: bool = False,
    ):
        """Run `task` on a job manager of its own for `key`, passing each
        result to `on_success` (and an error to `on_error`). `on_finished`
        is called when the task is finished, failed, or was stopped. It is only
        heard if this call starts the manager: a task queued behind a running one
        (same key) has no separate end.

        A task launched under a key that is already running waits for the
        tasks before it and then runs, in order. With `replace_pending` it
        instead takes the place of the tasks still waiting (never of the one
        running). `only_once` drops the new task if the key is in use."""
        if key in self.job_managers:
            if only_once:
                return
            self.job_managers[key].queue_job(
                Job(task, on_success, on_error, replace_pending)
            )
        else:
            manager = JobManager()
            self.job_managers[key] = manager

            @pyqtSlot()
            def on_manager_finished():
                if self.job_managers.get(key) is manager:
                    del self.job_managers[key]

            manager.signals.finished.connect(on_manager_finished)
            if on_finished is not None:
                manager.signals.finished.connect(on_finished)
            manager(Job(task, on_success, on_error))

    def close_threads(self):
        for key in self.job_managers:
            self.job_managers[key].quit()

    def close_thread(self, key: str):
        manager = self.job_managers.pop(key, None)
        if manager is not None:
            manager.quit()
