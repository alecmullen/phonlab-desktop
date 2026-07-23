from core.entity.audio_signal import AudioSignal
from core.usecase.use_case import UseCase
import phonlab as phon

class LoadAudio(UseCase):

    def __init__(self, filename):
        super().__init__()
        self.filename = filename

    def invoke(self) -> AudioSignal:
        original_x, original_fs = phon.loadsig(self.filename)
        y, fs = phon.prep_audio(original_x, original_fs, target_fs=16000, scale=True, pre=0.94, add_tiny_noise=True)

        return AudioSignal(y, fs)
    