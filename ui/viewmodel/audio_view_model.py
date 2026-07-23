from dataclasses import dataclass, field, replace
import numpy as np
from core.usecase.load_audio import LoadAudio, AudioSignal
from ui.model.audio_wave_model import AudioWaveModel, to_audio_wave_model
from ui.viewmodel.view_model import ViewModel
    
class AudioViewModel(ViewModel):
    def __init__(self):
        super().__init__()
        self.audio_wave_model = AudioWaveModel()

    def load_audio(self, filepath: str):
        self.loadAudioTask = LoadAudio(filepath)
        self.loadAudioTask(self.dispatch, self.on_error)

    def update_state(self, entity):
        if isinstance(entity, AudioSignal): 
            self.audio_wave_model = to_audio_wave_model(entity)
