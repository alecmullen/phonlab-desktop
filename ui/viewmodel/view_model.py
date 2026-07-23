from abc import abstractmethod
from collections.abc import Callable

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class ViewModel(QObject):
    state_changed = pyqtSignal(object)

    def subscribe(self, slot: Callable):
        self.state_changed.connect(slot)
