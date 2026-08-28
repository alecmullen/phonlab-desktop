import time

import numpy as np
from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot

from core.play_audio.audio_worker import AudioWorker
from core.play_audio.entity.latency_info import LatencyInfo
from core.play_audio.entity.playback_poll import PlaybackPoll


class AudioPlayer(QObject):
    playback_poll = pyqtSignal(object)
    playback_error = pyqtSignal(str)

    audio_queue = pyqtSignal(object, int)

    PLAYBACK_POLL_MS = 33
    STOP_TIMEOUT_S = 2.0

    def __init__(self, parent=None):
        super().__init__(parent)

        self._start_time = 0.0
        self._audible_start_time: float | None = None
        self._audio_length_time = 0.0
        self._latency = 0.0

        self._audio_thread = QThread()
        self._audio_worker = AudioWorker(self._on_latency)
        self.set_up_threading()

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(self.PLAYBACK_POLL_MS)
        self.poll_timer.timeout.connect(self._poll_playback)

    def set_up_threading(self):
        self._audio_worker.moveToThread(self._audio_thread)

        self._audio_worker.finished.connect(self._on_audio_finished)
        self._audio_worker.started.connect(self._on_audio_started)
        self._audio_worker.error.connect(self._on_error)

        self.audio_queue.connect(self._audio_worker.play)

        self._audio_thread.start()

    def _get_current_time(self) -> float:
        if self._audible_start_time is None:
            current_time = 0.0
        else:
            current_time = max(0.0, time.monotonic() - self._audible_start_time)
            current_time = min(current_time, self._audio_length_time)
        return current_time + self._start_time

    def play(self, audio_data: np.ndarray, fs: int, start_time: float):
        """Play audio using whatever the current default output device is."""
        self.stop()

        self._start_time = start_time
        self._audible_start_time = None
        self._audio_length_time = len(audio_data) / fs

        self.audio_queue.emit(audio_data, fs)

    @pyqtSlot()
    def _poll_playback(self):
        self.playback_poll.emit(
            PlaybackPoll(self._get_current_time(), self._latency, True)
        )

    @pyqtSlot()
    def _on_audio_started(self):
        self.poll_timer.start()

    @pyqtSlot()
    def _on_audio_finished(self):
        self.playback_poll.emit(PlaybackPoll(0.0, self._latency, False))
        self.poll_timer.stop()
        self._current_thread = None

    @pyqtSlot(object)
    def _on_latency(self, latency_info: LatencyInfo):
        self._latency = latency_info.latency
        self._audible_start_time = latency_info.audible_start_time

    def _on_error(self, message: str, thread: "AudioThread"):
        if thread is not self._current_thread:
            return
        self.playback_error.emit(message)
        self.poll_timer.stop()
        self._current_thread = None

    def stop(self):
        if self._audio_worker is not None:
            self._audio_worker.stop()
        self.poll_timer.stop()
