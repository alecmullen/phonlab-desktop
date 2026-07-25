from collections.abc import Callable

from PyQt6.QtCore import QObject, pyqtSignal

from core.usecase.use_case import UseCase


class ViewModel(QObject):
    state_changed = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        self.tasks: dict[str, UseCase] = {}

    def subscribe(self, slot: Callable):
        self.state_changed.connect(slot)
        
    def launch_use_case(self, key: str, use_case: UseCase, on_success: Callable, on_error: Callable):
        if key in self.tasks:
            self.tasks[key].quit()
        self.tasks[key] = use_case
        use_case(on_success, on_error)
