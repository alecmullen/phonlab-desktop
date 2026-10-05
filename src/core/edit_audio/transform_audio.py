import numpy as np
import phonlab as phon

from core.base.use_case_sync import UseCaseSync


class ScaleAudio(UseCaseSync[np.ndarray]):
    """Scale samples so their peak is `scale` dBFS, via phon.prep_audio()."""

    def __init__(self, x: np.ndarray, fs: int, scale: float):
        super().__init__()
        self.x = x
        self.fs = fs
        self.scale = scale

    def invoke(self) -> np.ndarray:
        y, _ = phon.prep_audio(
            self.x,
            self.fs,
            target_fs=self.fs,
            scale=self.scale,
            pre=0,
            add_tiny_noise=False,
        )
        return y.astype(self.x.dtype, copy=False)


class ReverseAudio(UseCaseSync[np.ndarray]):
    """Reverse the order of the samples."""

    def __init__(self, x: np.ndarray):
        super().__init__()
        self.x = x

    def invoke(self) -> np.ndarray:
        return self.x[::-1].copy()
