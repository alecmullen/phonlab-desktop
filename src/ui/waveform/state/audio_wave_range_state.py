from dataclasses import dataclass

from ui.base.state import State


@dataclass(frozen=True)
class AudioWaveScaleState(State):
    y_scale: float = 1.0
    scaled_y_max: float = 1.0
