import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QWidget

from res.constants import MAX_SGRAM_LENGTH
from ui.spectrogram.spectrogram_state import SpectrogramState
from ui.spectrogram.spectrogram_view_model import SpectrogramViewModel


class SpectrogramPlot(pg.PlotItem):
    def __init__(
        self,
        parent: QWidget | None = None,
        view_model: SpectrogramViewModel = None,
        linked_plot: pg.PlotItem | None = None,
        is_bottom_plot: bool = False,
    ):
        super().__init__(parent)

        self.view_model = view_model
        self.view_model.subscribe(self.on_state_change)

        self.setLabel("left", self.tr("Frequency"), units="Hz")
        self.getAxis("left").enableAutoSIPrefix(False)
        self.getAxis("left").setWidth(60)

        if is_bottom_plot:
            self.setLabel("bottom", self.tr("Time"), units="s")
            self.getAxis("bottom").enableAutoSIPrefix(False)
        else:
            self.getAxis("bottom").setStyle(showValues=False)

        self.showGrid(x=True, y=True, alpha=0.3)
        self.getViewBox().setMouseEnabled(x=False, y=False)
        self.getViewBox().rbScaleBox.hide()

        self.spec_img = pg.ImageItem()
        self.addItem(self.spec_img)
        lut = pg.colormap.get("CET-L1").getLookupTable(nPts=256)[::-1]
        self.spec_img.setLookupTable(lut)

        self.cursor_line = pg.InfiniteLine(angle=90, movable=False, pen="r")
        self.addItem(self.cursor_line, ignoreBounds=True)

        self.mark_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(color="g", width=2, style=Qt.PenStyle.DashLine),
        )
        self.addItem(self.mark_line, ignoreBounds=True)
        self.mark_line.setVisible(False)

        self.selection_region = pg.LinearRegionItem(
            values=[0, 0],
            brush=pg.mkBrush(0, 100, 200, 50),
            movable=False,
        )
        self.selection_region.setZValue(10)
        self.addItem(self.selection_region)
        self.selection_region.setVisible(False)

        self.getViewBox().setXLink(linked_plot)

        self.center_label = pg.LabelItem(
            self.tr(
                "Zoom to a chunk of {} seconds or shorter to see spectrogram"
            ).format(MAX_SGRAM_LENGTH),
            size="32pt",
            color="#A0A0A0",
        )
        self.center_label.setVisible(False)
        self.center_label.setParentItem(self.getViewBox())
        self.center_label.anchor(itemPos=(0.5, 0.5), parentPos=(0.5, 0.5))

        self.plot_spectrogram(self.view_model.sgram_state)

    @pyqtSlot(object)
    def on_state_change(self, model):
        if isinstance(model, SpectrogramState):
            self.plot_spectrogram(model)

    def plot_spectrogram(self, sgram: SpectrogramState):
        if not sgram.is_showing:
            self.display_window_too_big()
        else:
            self.populate_spectrogram(sgram)

    def populate_spectrogram(self, sgram: SpectrogramState):
        """Fill the spectrogram image with data"""

        self.center_label.setVisible(False)

        self.getViewBox().setLimits(yMin=0, yMax=sgram.f[-1])
        self.getViewBox().setYRange(sgram.f[0], sgram.f[-1])

        min, max = np.min(sgram.sxx_window), np.max(sgram.sxx_window)
        vmin = min + (max - min) * sgram.gray_cutoff

        self.spec_img.setImage(
            sgram.sxx_window.T,
            autoLevels=False,
            levels=(vmin, np.max(sgram.sxx_window)),
        )

        time_start = sgram.t_window[0]
        time_end = sgram.t_window[-1]
        freq_start = sgram.f[0]
        freq_end = sgram.f[-1]

        rect = pg.QtCore.QRectF(
            time_start, freq_start, time_end - time_start, freq_end - freq_start
        )
        self.spec_img.setRect(rect)

        return True

    @pyqtSlot(object)
    def on_mouse_moved(self, pos):
        x = self.getViewBox().mapSceneToView(pos).x()
        self.cursor_line.setPos(x)

    def set_cursor_position(self, x: float, visible: bool):
        self.cursor_line.setPos(x)
        self.cursor_line.setVisible(visible)

    def set_mark_position(self, x: float, visible: bool):
        self.mark_line.setPos(x)
        self.mark_line.setVisible(visible)

    def update_selection_region(self, box_left: float, xrange: float):
        if xrange > 0:
            self.selection_region.setRegion([box_left, box_left + xrange])
            self.selection_region.setVisible(True)
        else:
            self.selection_region.setVisible(False)

    def display_window_too_big(self):
        if self.spec_img:
            self.spec_img.clear()

        self.center_label.setVisible(True)

    def adjust_gray_scale(self, is_trackpad: bool, delta: float):
        if is_trackpad:
            adjustment = delta * 0.0005
        else:
            adjustment = delta * 0.01

        self.view_model.adjust_gray_scale(adjustment)
