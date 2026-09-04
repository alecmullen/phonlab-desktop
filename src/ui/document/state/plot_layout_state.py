from dataclasses import dataclass, field
from enum import Enum


class PlotType(Enum):
    WAVEFORM = 1
    SPECTROGRAM = 2
    ANNOTATION = 3


@dataclass(frozen=True)
class PlotLayoutState:
    plots: set[PlotType] = field(default_factory=lambda: {PlotType.WAVEFORM})

    def has_waveform(self):
        return PlotType.WAVEFORM in self.plots

    def has_spectrogram(self):
        return PlotType.SPECTROGRAM in self.plots

    def has_annotation(self):
        return PlotType.ANNOTATION in self.plots
