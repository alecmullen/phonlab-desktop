import threading
import time

import numpy as np
from PyQt6.QtCore import QObject, QThreadPool, QTimer, pyqtSignal, pyqtSlot

from core.play_audio.audio_thread import AudioThread
from core.play_audio.entity.latency_info import LatencyInfo
from core.play_audio.entity.playback_poll import PlaybackPoll


class AudioPlayer(QObject):
    playback_poll = pyqtSignal(object)
    playback_error = pyqtSignal(str)
    stop_signal = pyqtSignal()

    thread_pool: QThreadPool = QThreadPool.globalInstance()

    PLAYBACK_POLL_MS = 33

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        self._start_time = 0.0
        self._audible_start_time = float("inf")
        self._audio_length_time = 0.0
        self._latency = 0.0

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(self.PLAYBACK_POLL_MS)
        self.poll_timer.timeout.connect(self._poll_playback)

    def _get_current_time(self) -> float:
        current_time = max(0.0, time.monotonic() - self._audible_start_time)
        current_time = min(current_time, self._audio_length_time)
        return current_time + self._start_time

    def _is_playing(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def play(self, audio_data: np.ndarray, fs: int, start_time: float):
        """Play audio using whatever the current default output device is."""
        self.stop() 
        self._stop_event.clear()

        self._start_time = start_time
        self._audible_start_time = float("inf")
        self._audio_length_time = len(audio_data) / fs

        audio_thread = AudioThread(audio_data, fs)

        audio_thread.signals.finished.connect(self._on_thread_finished)
        audio_thread.signals.error.connect(self._on_error)
        audio_thread.signals.latency.connect(self._on_latency)

        self.stop_signal.connect(audio_thread.slots.stop)

        self.thread_pool.start(audio_thread)
        self.poll_timer.start()

    @pyqtSlot()
    def _poll_playback(self):
        self.playback_poll.emit(PlaybackPoll(self._get_current_time(), self._latency, True))

    @pyqtSlot()
    def _on_thread_finished(self):
        self.playback_poll.emit(PlaybackPoll(self._get_current_time(), self._latency, False))
        self.poll_timer.stop()

    @pyqtSlot(object)
    def _on_latency(self, latency_info: LatencyInfo):
        self._latency = latency_info.latency
        self._audible_start_time = latency_info.audible_start_time

    @pyqtSlot(str)
    def _on_error(self, str):
        self.playback_error.emit(str)
        self.poll_timer.stop()

    def stop(self):
        self.stop_signal.emit()
