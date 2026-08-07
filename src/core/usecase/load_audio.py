import phonlab as phon

from core.entity.audio_signal import AudioSignal
from core.usecase.use_case import UseCase


class LoadAudio(UseCase[AudioSignal]):
    def __init__(self, filename: str):
        self.filename = filename

    def invoke(self):
        original_x, original_fs = phon.loadsig(self.filename)
        x, fs = phon.prep_audio(
            original_x,
            original_fs,
            target_fs=16000,
            scale=True,
            pre=0.94,
            add_tiny_noise=True,
        )

        yield AudioSignal(x, fs)

    def stop(self):
        pass
