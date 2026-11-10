import numpy as np
import phonlab as phon
import soundfile as sf

from core.base.use_case_sync import UseCaseSync
from core.load_audio.entity.audio_signal import AudioSignal


class SaveAudio(UseCaseSync):
    def __call__(
        self,
        path: str,
        channels: list[AudioSignal],
        target_fs: int,
        scale: bool,
    ):
        prepped = []
        fs = target_fs
        for channel in channels:
            x, fs = phon.prep_audio(
                channel.x,
                channel.fs,
                target_fs=target_fs,
                scale=scale,
                pre=0,
                add_tiny_noise=False,
            )
            prepped.append(x)

        data = prepped[0] if len(prepped) == 1 else np.stack(prepped, axis=1)
        sf.write(path, data, fs, subtype="PCM_16")
