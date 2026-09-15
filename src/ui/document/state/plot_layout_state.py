from dataclasses import dataclass, field
from enum import Enum

from ui.base.state import State


class PlotType(Enum):
    WAVEFORM = 1
    SPECTROGRAM = 2
    ANNOTATION = 3


@dataclass(frozen=True)
class PlotLayoutState(State):
    plots: set[PlotType] = field(default_factory=lambda: {PlotType.WAVEFORM})

    def has_waveform(self) -> bool:
        return PlotType.WAVEFORM in self.plots

    def has_spectrogram(self) -> bool:
        return PlotType.SPECTROGRAM in self.plots

    def has_annotation(self) -> bool:
        return PlotType.ANNOTATION in self.plots
