from PyQt6.QtCore import pyqtSlot

from core.usecase.load_audio import AudioSignal, LoadAudio
from ui.model.audio_wave_model import to_audio_wave_model
from ui.viewmodel.view_model import ViewModel


class AudioViewModel(ViewModel):
    def __init__(self):
        super().__init__()

    def load_audio(self, filepath: str):
        self.loadAudioTask = LoadAudio(filepath)
        self.loadAudioTask(self.update_state, self.on_error)

    def update_state(self, entity):
        state_change = None
        if isinstance(entity, AudioSignal): 
            state_change = to_audio_wave_model(entity)

        if state_change:
            self.state_changed.emit(state_change)

    @pyqtSlot(object)
    def on_error(err):
        print(err.message)
