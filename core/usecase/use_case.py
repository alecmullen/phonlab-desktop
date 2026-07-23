from abc import ABC, abstractmethod

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot


class UseCaseWorker[T](QObject):

    result = pyqtSignal(object)
    error = pyqtSignal(Exception)

    def __init__(self, invoke):
        super().__init__()
        self._invoke = invoke

    @pyqtSlot()
    def invoke(self):
        try:
            result = self._invoke()
            self.result.emit(result)
        except Exception as err:
            self.error.emit(err)
            raise
        
class UseCase[T](ABC):

    @abstractmethod
    def invoke() -> T:
        pass

    def __call__(self, on_success, on_error):
        self.thread = QThread()
        self.worker = UseCaseWorker[T](self.invoke)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.invoke)
        self.worker.result.connect(on_success)
        self.worker.error.connect(on_error)

        self.worker.result.connect(self.thread.quit)
        self.worker.result.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()
