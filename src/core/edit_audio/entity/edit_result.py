from dataclasses import dataclass, field

from core.load_audio.entity.audio_signal import AudioSignal


@dataclass(frozen=True)
class EditResult:
    new_channel: AudioSignal = field(default_factory=lambda: AudioSignal())
    new_clip: AudioSignal = field(default_factory=lambda: AudioSignal())
    start_idx: int = 0
