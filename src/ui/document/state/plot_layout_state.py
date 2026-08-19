from dataclasses import dataclass, field
from enum import Enum


class PlotType(Enum):
    WAVEFORM = 1
    SPECTROGRAM = 2
    ANNOTATION = 3


@dataclass(frozen=True)
class PlotLayoutState:
    plots: set[PlotType] = field(default_factory=lambda: {PlotType.WAVEFORM})
