import numpy as np
import phonlab as phon
import soundfile as sf

from core.base.use_case_sync import UseCaseSync
from core.load_audio.entity.audio_signal import AudioSignal


class SaveAudio(UseCaseSync):
    def __init__(
        self,
        path: str,
        channels: list[AudioSignal],
        target_fs: int,
        scale: bool,
    ):
        super().__init__()
        self.path = path
        self.channels = channels
        self.target_fs = target_fs
        self.scale = scale

    def invoke(self):
        prepped = []
        fs = self.target_fs
        for channel in self.channels:
            x, fs = phon.prep_audio(
                channel.x,
                channel.fs,
                target_fs=self.target_fs,
                scale=self.scale,
                pre=0,
                add_tiny_noise=False,
            )
            prepped.append(x)

        data = prepped[0] if len(prepped) == 1 else np.stack(prepped, axis=1)
        sf.write(self.path, data, fs, subtype="PCM_16")
