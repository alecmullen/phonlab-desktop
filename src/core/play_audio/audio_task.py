import threading
import time

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QObject, pyqtSignal

from core.play_audio.entity.latency_info import LatencyInfo


class AudioTask(QObject):
    latency = pyqtSignal(object)

    def __init__(self, audio_data: np.ndarray, fs: int):
        super().__init__()
        self._audio_data = audio_data[..., None] if audio_data.ndim == 1 else audio_data
        self._fs = fs

        self._current_offset = 0
        self._is_first_chunk = True
        self._latency = 0.0

        self._should_stop = False

        self._finished_event = threading.Event()

    def __call__(self):
        # Force PortAudio to re-scan its device list
        if sd._initialized:
            sd._terminate()
            sd._initialize()

        audio_data = np.ascontiguousarray(self._audio_data, dtype="float32")

        # Fresh OutputStream with currently selected system default
        with self._open_stream(self._fs, audio_data.shape[1]):
            self._finished_event.wait(timeout=(len(self._audio_data) / self._fs) + 0.02)
            time.sleep(self._latency)

    def _audio_callback(self, outdata, frames, time_info, status):
        if self._is_first_chunk:
            self._latency = time_info.outputBufferDacTime - time_info.currentTime
            audible_start_time = time.monotonic() + self._latency
            self.latency.emit(LatencyInfo(self._latency, audible_start_time))
            self._is_first_chunk = False

        remainder = len(self._audio_data) - self._current_offset
        if remainder >= frames and not self._should_stop:
            outdata[:, :] = self._audio_data[
                self._current_offset : self._current_offset + frames
            ]
            self._current_offset += frames
        else:
            if remainder < frames and not self._should_stop:
                outdata[:remainder, :] = self._audio_data[self._current_offset :]
                outdata[remainder:, :].fill(0)

            raise sd.CallbackAbort()

    def _open_stream(self, fs: int, channels: int) -> sd.OutputStream:
        """Open an OutputStream, falling back to a more conservative latency
        if the driver rejects the previous choice (some Windows audio
        drivers can't honor a low-latency request)."""
        last_err: Exception | None = None
        for latency in ("low", "high", None):
            try:
                self._is_first_chunk = True
                return sd.OutputStream(
                    samplerate=fs,
                    blocksize=128,
                    channels=channels,
                    dtype="float32",
                    callback=self._audio_callback,
                    finished_callback=self._finished_event.set,
                    latency=latency,
                )
            except sd.PortAudioError as e:
                last_err = e
        raise last_err

    def stop(self):
        self._should_stop = True
