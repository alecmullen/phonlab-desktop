from abc import abstractmethod
from collections.abc import Callable
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

class ViewModel(QObject):
    state_changed = pyqtSignal()

    def subscribe(self, slot: Callable):
        self.state_changed.connect(slot)

    @abstractmethod
    def update_state(self, model):
        pass

    @pyqtSlot(object)
    def dispatch(self, model):
        self.update_state(model)
        self.state_changed.emit()

    @pyqtSlot(object)
    def on_error(self, err):
        print(err.message)
