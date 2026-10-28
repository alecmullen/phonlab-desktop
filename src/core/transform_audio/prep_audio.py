import phonlab as phon

from core.base.use_case import UseCase
from core.load_audio.entity.audio_signal import AudioSignal


class PrepAudio(UseCase[dict[int, AudioSignal]]):
    def __call__(
        self,
        raw_signals: dict[int, AudioSignal],
        target_fs: int,
        retained_channels: list[int],
        pre: float = 0,
        scale: bool | float = True,
        add_tiny_noise: bool = True,
    ):
        raw_channels = [raw_signals[idx] for idx in retained_channels]
        channels = {}
        for idx, raw in zip(retained_channels, raw_channels):
            x, prepped_fs = phon.prep_audio(
                raw.x,
                raw.fs,
                target_fs=target_fs,
                scale=scale,
                pre=pre,
                add_tiny_noise=add_tiny_noise,
            )
            channels[idx] = AudioSignal(x, prepped_fs)
        yield channels
