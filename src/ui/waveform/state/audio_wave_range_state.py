from dataclasses import dataclass


@dataclass(frozen=True)
class AudioWaveScaleState:
    y_scale: float = 1.0
    scaled_y_max: float = 1.0
