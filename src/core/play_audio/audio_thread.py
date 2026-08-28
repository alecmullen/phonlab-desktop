import time

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from core.play_audio.entity.latency_info import LatencyInfo


class AudioThread(QRunnable):

    TARGET_CHUNK_MS = 20 

    def __init__(self, audio_data: np.ndarray, fs: int):
        super().__init__()

        self.signals = AudioThreadSignals()
        self.slots = AudioThreadSlots(self)

        self._should_stop = False

        self._audio_data = audio_data[..., None] if audio_data.ndim == 1 else audio_data
        self._fs = fs

        self._current_offset = 0
        self._is_first_chunk = True
        self._latency = 0.0

    def run(self):
        try:
            # Force PortAudio to re-scan its device list
            if sd._initialized:
                sd._terminate()
                sd._initialize()

            audio_data = np.ascontiguousarray(self._audio_data, dtype="float32")

            # Fresh OutputStream with currently selected system default
            with self._open_stream(self._fs, audio_data.shape[1]):
                time.sleep(len(self._audio_data) / self._fs)

        except sd.PortAudioError as e:
            self.signals.error.emit(str(e))
        except Exception as e:
            self.signals.error.emit(str(e))
            raise

    def _audio_callback(self, outdata, frames, time_info, status):
        if self._is_first_chunk:
            self._latency = time_info.outputBufferDacTime - time_info.currentTime
            audible_start_time = time.monotonic() + self._latency
            self.signals.latency.emit(LatencyInfo(self._latency, audible_start_time))
            self._is_first_chunk = False

        remainder = len(self._audio_data) - self._current_offset
        if remainder >= frames and not self._should_stop:
            outdata[:, :] = self._audio_data[self._current_offset:self._current_offset + frames]
            self._current_offset += frames
        else:
            if remainder < frames and not self._should_stop:
                outdata[:remainder, :] = self._audio_data[self._current_offset:]
                outdata[remainder:, :].fill(0)

            time.sleep(self._latency)
            self.signals.finished.emit()
            raise sd.CallbackStop()

    def _open_stream(self, samplerate: int, channels: int) -> sd.OutputStream:
        """Open an OutputStream, falling back to a more conservative latency
        if the driver rejects the previous choice (some Windows audio
        drivers can't honor a low-latency request)."""
        last_err: Exception | None = None
        for latency in ("low", "high", None):
            try:
                return sd.OutputStream(
                    samplerate=samplerate,
                    blocksize=128,
                    channels=channels,
                    dtype="float32",
                    callback=self._audio_callback,
                    latency=latency,
                )
            except sd.PortAudioError as e:
                last_err = e
        raise last_err

    def stop(self):
        self._should_stop = True

class AudioThreadSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    latency = pyqtSignal(object)

class AudioThreadSlots(QObject):
    def __init__(self, audio_thread: AudioThread):
        super().__init__()
        self._audio_thread = audio_thread

    @pyqtSlot()
    def stop(self):
        self._audio_thread.stop()
            