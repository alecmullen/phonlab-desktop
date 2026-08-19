import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QWidget
from pyqtgraph import PlotDataItem


class AudioWavePlot(pg.PlotItem):
    def __init__(self, parent: QWidget | None = None, is_bottom_plot: bool = False):
        super().__init__(parent)

        self.wave_curve: PlotDataItem | None = None

        self.setLabel("left", self.tr("Amplitude"))
        self.showGrid(x=True, y=True, alpha=0.3)
        self.getAxis("left").enableAutoSIPrefix(False)

        if is_bottom_plot:
            self.setLabel("bottom", self.tr("Time"), units="s")
            self.getAxis("bottom").enableAutoSIPrefix(False)
        else:
            self.getAxis("bottom").setStyle(showValues=False)

        self.vb.setMouseEnabled(x=False, y=False)
        self.vb.rbScaleBox.hide()
        self.vb.setMouseMode(pg.ViewBox.RectMode)

        self.selection_region = pg.LinearRegionItem(
            values=[0, 0],
            brush=pg.mkBrush(0, 100, 200, 30),
            movable=False,
        )
        self.addItem(self.selection_region)
        self.selection_region.setVisible(False)

        self.cursor_line = pg.InfiniteLine(angle=90, movable=False, pen="r")
        self.addItem(self.cursor_line, ignoreBounds=True)

    def plot_wave(
        self,
        t: np.ndarray,
        x: np.ndarray,
        start: int,
        end: int,
        max_x: float,
        min_x: float,
    ):
        limit = max(abs(min_x), abs(max_x))
        self.setYRange(-limit, limit, padding=0.05)
        self.vb.setLimits(yMin=-limit, yMax=limit)
        self.vb.setLimits(xMin=0, xMax=t[-1])
        self.enableAutoRange(axis="y", enable=False)

        self.wave_curve = self.plot(t[start:end], x[start:end], pen="b")
        self.setXRange(t[start], t[end], padding=0)

    def update_wave(self, t: np.ndarray, x: np.ndarray, tmax: float):
        self.wave_curve.setData(t, x)
        self.setXRange(t[0], tmax, padding=0)

    def update_selection_region(self, box_left, xrange):
        if xrange > 0:
            self.selection_region.setRegion([box_left, box_left + xrange])
            self.selection_region.setVisible(True)
        else:
            self.selection_region.setVisible(False)

    @pyqtSlot(float)
    def on_mouse_moved(self, x: float):
        self.cursor_line.setPos(x)

    def clear(self):
        self.wave_curve = None
