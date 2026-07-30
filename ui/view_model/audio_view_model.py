from dataclasses import replace

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QTimer, pyqtSlot

from core.entity.spectrogram import Spectrogram
from core.usecase.compute_sgram import ComputeSpectrogram
from core.usecase.load_audio import AudioSignal, LoadAudio
from core.usecase.play_audio import PlayAudio
from ui.state.audio_wave_state import AudioWaveState, to_audio_wave_state
from ui.state.full_audio_state import FullAudioState
from ui.state.select_state import SelectState
from ui.state.sgram_state import SpectrogramState, to_spectrogram_model
from ui.state.zoom_to_selection import ZoomToSelection
from ui.view_model.view_model import ViewModel


class AudioViewModel(ViewModel):
    
    def __init__(self):
        super().__init__()
        self.full_audio_state = FullAudioState()
        self.audio_wave_state: AudioWaveState = AudioWaveState()
        self.sgram_state: SpectrogramState = SpectrogramState()
        self.is_audio_playing = False
        self.select_state: SelectState = SelectState()

        self.click_timer: QTimer | None = None

    def load_audio(self, filepath: str):
        @pyqtSlot(object)
        def on_success(audio_signal: AudioSignal):
            self.audio_wave_state = to_audio_wave_state(audio_signal)
            self.full_audio_state = FullAudioState(audio_signal.x, audio_signal.fs)
            self.state_changed.emit(self.audio_wave_state)

        use_case = LoadAudio(filepath)
        self.launch_use_case(use_case, on_success, self.on_error)

    def compute_sgram(self, x: np.ndarray, fs: int, start: float, total_duration: float):
        duration = len(x) / fs

        @pyqtSlot(object)
        def on_success(sgram: Spectrogram):
            self.sgram_state = to_spectrogram_model(sgram, start, duration, total_duration)
            self.state_changed.emit(self.sgram_state)

        use_case = ComputeSpectrogram(x, fs)
        self.launch_use_case(use_case, on_success, self.on_error)

    def play_audio(self, x, fs):
        if self.is_audio_playing:
            self.stop_audio()

        @pyqtSlot(object)
        def on_success():
            self.is_audio_playing = False

        use_case = PlayAudio(x, fs)
        self.is_audio_playing = True
        self.launch_use_case(use_case, on_success, self.on_error)

    def stop_audio(self):
        sd.stop()
            
    def start_selection(self, x: float):
        self.select_state = replace(self.select_state, is_selected=True, sel_start=x, sel_end=x, sel_anchor=x)
        self.state_changed.emit(self.select_state)

    def continue_selection(self, x: float):
        sel_start = self.select_state.sel_start
        sel_end = self.select_state.sel_end

        if x >= self.select_state.sel_anchor:
            sel_start = self.select_state.sel_anchor
            sel_end = min(x, self.audio_wave_state.t[-1])
        elif x < self.select_state.sel_start:
            sel_start = max(x, 0.0)
            sel_end = self.select_state.sel_anchor

        sel_message = self.tr("Select: {:.3f} to {:.3f} ({:.3f}s)").format(sel_start, sel_end, sel_end - sel_start)
        self.select_state = replace(self.select_state, sel_start=sel_start, sel_end=sel_end, sel_message=sel_message)
        self.state_changed.emit(self.select_state)

    def remove_selection(self):
        self.select_state = SelectState()
        self.state_changed.emit(self.select_state)

    def zoom_if_in_selection(self, x: float):
        if self.select_state.sel_end > x > self.select_state.sel_start:
            state_change = ZoomToSelection(self.select_state.sel_start, self.select_state.sel_end)
            self.state_changed.emit(state_change)
            
    def play_selected_audio(self):
        start = int(self.select_state.sel_start * self.full_audio_state.fs)
        end = int(self.select_state.sel_end * self.full_audio_state.fs)

        if start != end:
            section = self.full_audio_state.x[start:end]
            self.play_audio(section, self.full_audio_state.fs)

    @pyqtSlot(object)
    def on_error(self, err):
        print(err)
