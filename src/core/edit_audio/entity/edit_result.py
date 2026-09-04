from dataclasses import dataclass

from core.load_audio.entity.audio_signal import AudioSignal


@dataclass(frozen=True)
class EditResult:
    new_channel: AudioSignal | None = None
    new_clip: AudioSignal | None = None
    start_idx: int | None = None
