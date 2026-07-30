from collections.abc import Callable

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from core.task.job import Job
from core.task.task_worker import TaskManager
from core.usecase.use_case import UseCase


class ViewModel(QObject):

    state_changed = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.tasks: dict[str, TaskManager] = {}

    def subscribe(self, slot: Callable):
        self.state_changed.connect(slot)
        
    def launch_use_case(self, use_case: UseCase, on_success: Callable, on_error: Callable):
        if use_case.key in self.tasks:
            self.tasks[use_case.key].queue_job(Job(use_case.invoke, on_success, on_error))
        else:
            self.tasks[use_case.key] = TaskManager()
            self.tasks[use_case.key](Job(use_case.invoke, on_success, on_error))
            
            @pyqtSlot()
            def on_finished():
                del self.tasks[use_case.key]

            self.tasks[use_case.key].signals.finished.connect(on_finished)

    def close_threads(self):
        for key in self.tasks:
            self.tasks[key].quit()
