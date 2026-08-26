import threading
import time

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QObject, pyqtSignal


class AudioPlayer(QObject):
    playback_finished = pyqtSignal()
    playback_error = pyqtSignal(str)
    stream_latency = pyqtSignal(float)  # seconds, emitted once per play()

    TARGET_CHUNK_MS = 20  # target chunk duration, tweak if needed

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._current_sample = 0
        self._total_samples = 0
        self._start_sample = 0
        self._samplerate = 1
        self._audible_start_time = 0.0  # time.monotonic() when sample 0 becomes audible

    @property
    def current_sample(self) -> int:
        if not self.is_playing:
            return self._start_sample + self._current_sample

        elapsed = max(0.0, time.monotonic() - self._audible_start_time)
        elapsed_samples = min(int(elapsed * self._samplerate), self._total_samples)
        return self._start_sample + elapsed_samples

    @property
    def current_time(self) -> float:
        return self.current_sample / self._samplerate

    @property
    def is_playing(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def play(self, audio_data: np.ndarray, samplerate: int, start_sample: int = 0):
        """Play audio using whatever the current default output device is."""
        self.stop()  # Stop any existing playback first
        self._stop_event.clear()

        self._current_sample = 0
        self._total_samples = len(audio_data)
        self._start_sample = start_sample
        self._samplerate = samplerate
        # Sentinel: the real value is set once the stream actually opens.
        # Without this, current_sample could read the stale value from
        # __init__ or a previous play() before that happens, and clamp to
        # "fully finished" instead of 0.
        self._audible_start_time = float("inf")

        self._thread = threading.Thread(
            target=self._playback_thread,
            args=(audio_data, samplerate),
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._current_sample = 0

    def _refresh_device_table(self):
        """Force PortAudio to re-scan its device list.

        PortAudio only builds this table once, at the first `import
        sounddevice`, so `device=None` would otherwise keep resolving to
        whatever was the default output device at that time (e.g. it
        won't notice headphones plugged in after startup)."""
        sd._terminate()
        sd._initialize()

    def _open_stream(self, samplerate: int, channels: int) -> sd.OutputStream:
        """Open an OutputStream, falling back to a more conservative latency
        if the driver rejects the previous choice (some Windows audio
        drivers can't honor a low-latency request)."""
        last_err: Exception | None = None
        for latency in ("low", "high", None):
            try:
                return sd.OutputStream(
                    samplerate=samplerate,
                    channels=channels,
                    dtype="float32",
                    latency=latency,
                )
            except sd.PortAudioError as e:
                last_err = e
        raise last_err

    def _playback_thread(self, audio_data: np.ndarray, samplerate: int):
        try:
            self._refresh_device_table()

            audio_data = np.ascontiguousarray(audio_data, dtype="float32")
            channels = audio_data.shape[1] if audio_data.ndim > 1 else 1

            # Compute chunk size from target duration and actual sample rate
            chunk_size = int(samplerate * self.TARGET_CHUNK_MS / 1000)

            # Fresh OutputStream with no explicit device = always uses
            # whatever is currently selected as the system default
            with self._open_stream(samplerate, channels) as stream:
                # Sample 0 doesn't become audible until one latency period
                # after the stream starts.
                self._audible_start_time = time.monotonic() + stream.latency
                self.stream_latency.emit(stream.latency)

                offset = 0
                while offset < len(audio_data) and not self._stop_event.is_set():
                    chunk = audio_data[offset : offset + chunk_size]
                    stream.write(chunk)
                    offset += chunk_size

                if not self._stop_event.is_set():
                    # stream.stop() (below, on context exit) only waits for
                    # PortAudio's own buffer to drain. Some backends (e.g.
                    # Bluetooth via Core Audio) buffer more audio downstream
                    # than that, so without this the tail gets cut off, or a
                    # clip shorter than the latency doesn't play at all.
                    time.sleep(stream.latency)

            if not self._stop_event.is_set():
                self._current_sample = self._total_samples
                self.playback_finished.emit()

        except Exception as e:
            self.playback_error.emit(str(e))
