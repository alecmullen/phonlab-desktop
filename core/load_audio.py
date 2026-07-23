from dataclasses import dataclass

from core.use_case import UseCase
import phonlab as phon
import numpy as np

@dataclass
class LoadAudioResponse:
    y: np.ndarray
    fs: int

class LoadAudio(UseCase):

    def __init__(self, filename):
        self.filename = filename

    def invoke(self):
        original_x, original_fs = phon.loadsig(self.filename)
        y, fs = phon.prep_audio(original_x, original_fs,target_fs=16000, scale=True, pre=0.94, add_tiny_noise=True)

        return LoadAudioResponse(y, fs)
    