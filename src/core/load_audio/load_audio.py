import phonlab as phon

from core.base.use_case import UseCase
from core.load_audio.entity.audio_signal import AudioSignal


class LoadAudio(UseCase[dict[int, AudioSignal]]):
    def __init__(self, filename: str):
        self.filename = filename

    def invoke(self):
        *original_channels, original_fs = phon.loadsig(self.filename)
        signals = {}
        for idx, x in enumerate(original_channels):
            signals[idx] = AudioSignal(x, original_fs)
        yield signals

    def stop(self):
        pass
