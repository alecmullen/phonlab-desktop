from dataclasses import dataclass, field, replace
import numpy as np
from core.load_audio import LoadAudio, LoadAudioResponse
from ui.viewmodel.view_model import ViewModel

@dataclass(frozen=True)
class AudioViewState:
    y: np.ndarray = field(default_factory=lambda: np.zeros(0))
    fs: int = 0
    miny: float = 0.0
    maxy: float = 0.0
    yrange: float = 0.0
    t: np.ndarray = field(default_factory=lambda: np.zeros(0))
    
class AudioViewModel(ViewModel):
    def __init__(self):
        super().__init__(AudioViewState())

    def load_audio(self, filepath: str):
        loadAudioTask = LoadAudio(filepath)
        loadAudioTask(self.dispatch, print)

    def dispatch_load_audio_response(self, response: LoadAudioResponse):
        y, fs = response.y, response.fs
        miny = np.min(y)
        maxy = np.max(y)
        yrange = maxy - miny
        t = np.arange(len(y)) / fs

        self.state = replace(self.state, y=y, fs=fs, miny=miny, maxy=maxy, yrange=yrange, t=t)

    def on_dispatch(self, action):
        if isinstance(action, LoadAudioResponse): 
            self.dispatch_load_audio_response(action)
