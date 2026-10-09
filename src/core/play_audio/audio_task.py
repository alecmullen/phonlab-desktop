import threading
import time

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QObject, pyqtSignal

from core.play_audio.entity.latency_info import LatencyInfo
from res.constants import (
    PLAYBACK_FINISH_TIMEOUT_MARGIN_S,
    PLAYBACK_POST_ROLL_S,
    PLAYBACK_PRE_ROLL_S,
)

BLOCK_SIZE = 2048


class AudioTask(QObject):
    latency = pyqtSignal(object)

    def __init__(self, audio_data: np.ndarray, fs: int):
        super().__init__()
        self._audio_data = audio_data[..., None] if audio_data.ndim == 1 else audio_data
        self._fs = fs

        self._current_offset = 0
        self._is_first_chunk = True
        self._latency = 0.0
        self._pre_roll_s = 0.0

        self._should_stop = False

        self._finished_event = threading.Event()

    def __call__(self):
        # Force PortAudio to re-scan its device list
        if sd._initialized:
            sd._terminate()
            sd._initialize()

        self._audio_data = self._pad_with_silence(self._audio_data)

        # Fresh OutputStream with currently selected system default
        with self._open_stream(self._fs, self._audio_data.shape[1]):
            # The stream sets this event itself once the audio has played out
            # (or been aborted), so the timeout is only a safety net. It must
            # allow for the variable delay before the first callback; closing
            # the stream early would cut off the queued tail of the audio.
            self._finished_event.wait(
                timeout=(len(self._audio_data) / self._fs)
                + PLAYBACK_FINISH_TIMEOUT_MARGIN_S
            )
            time.sleep(self._latency)

    def _pad_with_silence(self, audio_data: np.ndarray) -> np.ndarray:
        channels = audio_data.shape[1]
        pre = np.zeros(
            (round(PLAYBACK_PRE_ROLL_S * self._fs), channels), dtype="float32"
        )
        post = np.zeros(
            (round(PLAYBACK_POST_ROLL_S * self._fs), channels), dtype="float32"
        )
        self._pre_roll_s = PLAYBACK_PRE_ROLL_S
        return np.ascontiguousarray(
            np.concatenate([pre, audio_data.astype("float32", copy=False), post])
        )

    def _audio_callback(
        self,
        outdata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ):
        if self._is_first_chunk:
            self._latency = time_info.outputBufferDacTime - time_info.currentTime  # ty: ignore[unresolved-attribute]
            audible_start_time = time.monotonic() + self._latency + self._pre_roll_s
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

            # CallbackStop drains already-queued audio (needed for devices with
            # deep output buffers, e.g. Bluetooth); abort only on user stop.
            if self._should_stop:
                raise sd.CallbackAbort()
            raise sd.CallbackStop()

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
                    blocksize=BLOCK_SIZE,
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
