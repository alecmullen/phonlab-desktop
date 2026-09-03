import phonlab as phon

from core.base.use_case import UseCase
from core.load_audio.entity.audio_signal import AudioSignal


class PrepAudio(UseCase[dict[AudioSignal]]):
    def __init__(
        self,
        raw_signals: list[AudioSignal],
        target_fs: int,
        retained_channels: list[int],
    ):
        self.raw_signals = raw_signals
        self.target_fs = target_fs
        self.retained_channels = retained_channels

        self.should_stop = False

    def invoke(self):
        raw_channels = [self.raw_signals[idx] for idx in self.retained_channels]
        channels = {}
        for idx, raw in zip(self.retained_channels, raw_channels):
            if self.should_stop:
                return
            x, prepped_fs = phon.prep_audio(
                raw.x, raw.fs, target_fs=self.target_fs, scale=True, pre=0.94, add_tiny_noise=True
            )
            channels[idx] = AudioSignal(x, prepped_fs)
        yield channels

    def stop(self):
        self.should_stop = True
