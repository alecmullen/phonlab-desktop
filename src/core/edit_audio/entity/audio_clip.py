from dataclasses import dataclass, field

from core.load_audio.entity.audio_signal import AudioSignal


@dataclass(frozen=True)
class AudioClip:
    """The copy/cut/paste clipboard payload: one channel for a mono clip,
    two (indexed 0 and 1) for a stereo clip."""

    channels: dict[int, AudioSignal] = field(default_factory=dict)

    @property
    def is_stereo(self) -> bool:
        return len(self.channels) == 2
