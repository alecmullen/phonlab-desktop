import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QWidget

from ui.document.state.sgram_state import SpectrogramState


class SpectrogramPlot(pg.PlotItem):
    def __init__(self, parent: QWidget | None = None, linked_plot: pg.PlotItem | None = None):
        super().__init__(parent)

        self.setLabel("left", self.tr("Frequency"), units="Hz")
        self.getAxis("left").enableAutoSIPrefix(False)
        self.getAxis("left").setWidth(60)

        self.setLabel("bottom", self.tr("Time"), units="s")
        self.getAxis("bottom").enableAutoSIPrefix(False)

        self.showGrid(x=True, y=True, alpha=0.3)
        self.setMouseEnabled(x=False, y=False)
        self.getViewBox().rbScaleBox.hide()

        self.spec_img = pg.ImageItem()
        self.addItem(self.spec_img)
        lut = pg.colormap.get("CET-L1").getLookupTable(nPts=256)[::-1]
        self.spec_img.setLookupTable(lut)

        self.cursor_line = pg.InfiniteLine(angle=90, movable=False, pen="r")
        self.addItem(self.cursor_line, ignoreBounds=True)

        self.selection_region = pg.LinearRegionItem(
            values=[0, 0],
            brush=pg.mkBrush(0, 100, 200, 50),
            movable=False,
        )
        self.selection_region.setZValue(10)
        self.addItem(self.selection_region)
        self.selection_region.setVisible(False)

        self.setXLink(linked_plot)

    def populate_spectrogram(self, sgram: SpectrogramState, gray_cutoff: float):
        """Fill the spectrogram image with data"""
        
        self.vb.setLimits(yMin=0, yMax=sgram.f[-1])
        self.setYRange(sgram.f[0], sgram.f[-1])

        vmin = (
                np.min(sgram.sxx) + (np.max(sgram.sxx) - np.min(sgram.sxx)) * gray_cutoff
        )
        self.spec_img.setImage(
            sgram.sxx.T, autoLevels=False, levels=(vmin, np.max(sgram.sxx))
        )

        time_start = sgram.t[0]
        time_end = sgram.t[-1]
        freq_start = sgram.f[0]
        freq_end = sgram.f[-1]

        rect = pg.QtCore.QRectF(
            time_start, freq_start, time_end - time_start, freq_end - freq_start
        )
        self.spec_img.setRect(rect)

        return True

    @pyqtSlot(float)
    def on_mouse_moved(self, x: float):
        self.cursor_line.setPos(x)
        
    def update_selection_region(self, box_left: float, xrange: float):
        if xrange > 0:
            self.selection_region.setRegion([box_left, box_left + xrange])
            self.selection_region.setVisible(True)
        else:
            self.selection_region.setVisible(False)
    
    def clear(self):
        if self.spec_img:
            self.spec_img.clear()
