import phonlab as phon

from core.entity.audio_signal import AudioSignal
from core.usecase.use_case import UseCase


class LoadAudio(UseCase):

    def __init__(self, filename):
        self.filename = filename

    def invoke(self) -> AudioSignal:
        original_x, original_fs = phon.loadsig(self.filename)
        x, fs = phon.prep_audio(original_x, original_fs, target_fs=16000, scale=True, pre=0.94, add_tiny_noise=True)

        return AudioSignal(x, fs)
    