import time

import numpy as np
import sounddevice as sd

from core.entity.playback_poll import PlaybackPoll
from core.usecase.use_case import UseCase

TARGET_CHUNK_MS = 20

class PlayAudio(UseCase[PlaybackPoll]):
    def __init__(self, audio_data: np.ndarray, fs: int, start_time: float):
        self._audio_data = audio_data
        self._fs = fs
        self._start_time = start_time
        self._audible_start_time = float("inf")
        self._should_stop = False
        self._latency = 0.0
        self._is_playing = True

    def _get_current_time(self):
        current_time = max(0.0, time.monotonic() - self._audible_start_time)
        current_time = min(current_time, len(self._audio_data / self._fs))
        return current_time + self._start_time

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

    def invoke(self):
        try:
            self._refresh_device_table()
            audio_data = np.ascontiguousarray(self._audio_data, dtype="float32")
            channels = audio_data.shape[1] if audio_data.ndim > 1 else 1
    
            chunk_size = int(self._fs * TARGET_CHUNK_MS / 1000)
    
            # Fresh OutputStream with currently selected system default device
            with self._open_stream(self._fs, channels) as stream:
                
                self._audible_start_time = time.monotonic() + stream.latency
    
                offset = 0
                while offset < len(audio_data) and not self._should_stop:
                    chunk = audio_data[offset : offset + chunk_size]
                    stream.write(chunk)
                    offset += chunk_size

                    yield PlaybackPoll(self._get_current_time(), self._latency, self._is_playing)
    
                if not self._should_stop:
                    time.sleep(stream.latency)

                self._is_playing = False
                yield PlaybackPoll(self._get_current_time(), self._latency, self._is_playing)

        except RuntimeError as e:
            print(f"Audio playback error: {e}")

    def _refresh_device_table(self):
        """Force PortAudio to re-scan its device list"""
        sd._terminate()
        sd._initialize()

    def stop(self):
        self.should_stop = True