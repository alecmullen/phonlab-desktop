import phonlab as phon

from core.base.use_case import UseCase
from core.load_audio.entity.audio_document import AudioDocument
from core.load_audio.entity.audio_signal import AudioSignal
from res.constants import MAX_SGRAM_LENGTH


class LoadAudio(UseCase[AudioDocument]):
    def __init__(
        self,
        filename: str,
        target_fs: int,
        channel_mode: str,
        retained_channels: list[int],
        primary_channel: int,
    ):
        self.filename = filename
        self.target_fs = target_fs
        self.channel_mode = channel_mode
        self.retained_channels = retained_channels
        self.primary_channel = primary_channel

    def _prep_channels(self, raw_channels, fs) -> dict[int, AudioSignal]:
        channels = {}
        for idx, raw in zip(self.retained_channels, raw_channels):
            x, prepped_fs = phon.prep_audio(
                raw,
                fs,
                target_fs=self.target_fs,
                scale=False,
                pre=0.94,
                add_tiny_noise=True,
            )
            channels[idx] = AudioSignal(x, prepped_fs)
        return channels

    def invoke(self):
        # Yield a fast preview of just the first window first, so there's
        # something on screen immediately
        *preview_raw, preview_fs = phon.loadsig(
            self.filename, chansel=self.retained_channels, duration=MAX_SGRAM_LENGTH
        )
        preview_channels = self._prep_channels(preview_raw, preview_fs)
        yield AudioDocument(
            channels=preview_channels,
            primary_channel=self.primary_channel,
            channel_mode=self.channel_mode,
            is_preview=True
        )

        # Full load of every native channel at its native rate, unprocessed.
        # Emit prepped channels and originals
        *original_channels, original_fs = phon.loadsig(self.filename)
        full_raw = [original_channels[idx] for idx in self.retained_channels]
        full_channels = self._prep_channels(full_raw, original_fs)

        yield AudioDocument(
            channels=full_channels,
            primary_channel=self.primary_channel,
            channel_mode=self.channel_mode,
            original_channels=original_channels,
            original_fs=original_fs,
        )

    def stop(self):
        pass
