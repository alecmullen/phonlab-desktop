import numpy as np
import phonlab as phon
import soundfile as sf

from core.base.use_case_sync import UseCaseSync


class SaveAudio(UseCaseSync):
    def __init__(
        self, path: str, raw_x: np.ndarray, raw_fs: int, target_fs: int, scale: bool
    ):
        super().__init__()
        self.path = path
        self.raw_x = raw_x
        self.raw_fs = raw_fs
        self.target_fs = target_fs
        self.scale = scale

    def invoke(self):
        x, fs = phon.prep_audio(
            self.raw_x,
            self.raw_fs,
            target_fs=self.target_fs,
            scale=self.scale,
            pre=0,
            add_tiny_noise=False,
        )
        sf.write(self.path, x, fs, subtype="PCM_16")
