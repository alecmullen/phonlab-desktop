import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from core.play_audio.audio_task import AudioTask


class AudioWorker(QObject):
    started = pyqtSignal()
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, latency_slot):
        super().__init__()
        self._task: AudioTask | None = None

        self._latency_slot = latency_slot

    @pyqtSlot(object, int)
    def play(self, audio_data: np.ndarray, fs: int):
        try:
            self.started.emit()
            if self._task is not None:
                del self._task
            self._task = AudioTask(audio_data, fs)
            self._task.latency.connect(self._latency_slot)
            self._task()
        except sd.PortAudioError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(str(e))
            raise
        self.finished.emit()

    def stop(self):
        if self._task is not None:
            self._task.stop()
