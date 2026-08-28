import numpy as np

from core.base.use_case import UseCase
from core.load_audio.entity.audio_document import AudioDocument
from core.load_audio.prep_channel import prep_channel


class LoadAudioFromSamples(UseCase[AudioDocument]):
    def __init__(self, x: np.ndarray, fs: int, target_fs: int):
        self.x = x
        self.fs = fs
        self.target_fs = target_fs

    def invoke(self):
        yield AudioDocument(
            channels={0: prep_channel(self.x, self.fs, self.target_fs)},
            primary_channel=0,
            channel_mode="mono",
            original_channels=[self.x],
            original_fs=self.fs,
        )

    def stop(self):
        pass
