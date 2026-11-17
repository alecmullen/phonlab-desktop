from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum

from ui.base.state import State


class PlotType(Enum):
    WAVEFORM = 1
    SPECTROGRAM = 2
    ANNOTATION = 3


def plot_names(plots: Iterable[PlotType]) -> list[str]:
    """Stable names for storing a set of plots, in display order"""
    return [plot.name.lower() for plot in sorted(plots, key=lambda p: p.value)]


def plots_from_names(names: Iterable[str]) -> frozenset[PlotType]:
    """The plots for stored names; unknown names are ignored. A layout always
    has at least one plot, so an empty result falls back to the waveform."""
    plots = {
        PlotType[name.upper()] for name in names if name.upper() in PlotType.__members__
    }
    return frozenset(plots or {PlotType.WAVEFORM})


@dataclass(frozen=True)
class PlotLayoutState(State):
    plots: set[PlotType] = field(default_factory=lambda: {PlotType.WAVEFORM})

    def has_waveform(self) -> bool:
        return PlotType.WAVEFORM in self.plots

    def has_spectrogram(self) -> bool:
        return PlotType.SPECTROGRAM in self.plots

    def has_annotation(self) -> bool:
        return PlotType.ANNOTATION in self.plots
