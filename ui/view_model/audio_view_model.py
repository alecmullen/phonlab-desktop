import numpy as np
from PyQt6.QtCore import pyqtSlot

from core.entity.spectrogram import Spectrogram
from core.usecase.compute_sgram import ComputeSpectrogram
from core.usecase.load_audio import AudioSignal, LoadAudio
from ui.state.audio_wave_state import to_audio_wave_state
from ui.state.sgram_state import to_spectrogram_model
from ui.view_model.view_model import ViewModel


class AudioViewModel(ViewModel):

    def load_audio(self, filepath: str):
        @pyqtSlot(object)
        def on_success(audio_signal: AudioSignal):
            self.audio_wave_state = to_audio_wave_state(audio_signal)
            self.state_changed.emit(self.audio_wave_state)

        use_case = LoadAudio(filepath)
        self.launch_use_case("load_audio", use_case, on_success, self.on_error)

    def compute_sgram(self, x: np.ndarray, fs: int, start: float, total_duration: float):
        duration = len(x) / fs

        @pyqtSlot(object)
        def on_success(sgram: Spectrogram):
            self.sgram_state = to_spectrogram_model(sgram, start, duration, total_duration)
            self.state_changed.emit(self.sgram_state)

        use_case = ComputeSpectrogram(x, fs)
        self.launch_use_case("sgram", use_case, on_success, self.on_error)

    @pyqtSlot(object)
    def on_error(self, err):
        print(err)
