from dataclasses import dataclass, field

from core.load_audio.entity.audio_signal import AudioSignal


@dataclass(frozen=True)
class EditResult:
    new_audio: dict[int, AudioSignal] = field(default_factory=dict)
    new_clip: dict[int, AudioSignal] = field(default_factory=dict)
    start_idx: int = 0
    # REPLACE only: the samples that new_clip overwrote
    replaced_clip: dict[int, AudioSignal] = field(default_factory=dict)
