import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget

from ui.state.sgram_state import SpectrogramState


class SpectrogramPlot(pg.PlotItem):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

    def plot_spectrogram(self, sgram: SpectrogramState, linked_plot: pg.PlotWidget, gray_cutoff: float):
        self.setLabel("left", "Frequency", units="Hz")
        self.setLabel("bottom", "Time", units="s")
        self.showGrid(x=True, y=True, alpha=0.3)

        self.vb.setMouseEnabled(x=False, y=False)
        self.vb.rbScaleBox.hide()
        self.vb.setLimits(xMin=0, xMax=sgram.t[-1])

        self.vb.setLimits(yMin=0, yMax=sgram.f[-1])
        self.setYRange(sgram.f[0], sgram.f[-1])
        self.getAxis("left").enableAutoSIPrefix(False)

        self.spec_img = pg.ImageItem()
        self.addItem(self.spec_img)

        lut = pg.colormap.get("CET-L1").getLookupTable(nPts=256)[::-1]
        self.spec_img.setLookupTable(lut)

        selection_region_spec = pg.LinearRegionItem(
            values=[0, 0],
            brush=pg.mkBrush(0, 100, 200, 50),
            movable=False,
            bounds=[0, sgram.t[-1]],
        )
        selection_region_spec.setZValue(10)
        self.addItem(selection_region_spec)
        selection_region_spec.setVisible(False)

        v_line_spec = pg.InfiniteLine(angle=90, movable=False, pen="r")
        self.addItem(v_line_spec, ignoreBounds=True)

        self.getAxis("left").setWidth(60)

        self.setXLink(linked_plot)
        #
        # if sgram.duration > 5.0:
        #     self.message_label.setText(
        #         "Zoom to a chunk of 5 seconds or shorter to see spectrogram"
        #     )
        #     return
        #
        # if self.freqs is None:
        #     self.message_label.setText(
        #         "Spectrogram hasn't started computing, please wait..."
        #     )
        #     return

        # if sgram.t[self.start] > self.max_time_computed:
        #     self.message_label.setText(
        #         f"Spectrogram not yet computed for this time range (computed up to {self.max_time_computed:.2f}s)"
        #     )
        #     return

        self.populate_spectrogram(sgram, gray_cutoff)

        # # Update message
        # if self.sgram_partial and not self.sgram_ready:
        #     self.message_label.setText(
        #         f"Showing partial spectrogram (still computing)... Duration shown {sgram.duration:.3f} seconds"
        #     )
        # else:
        #     self.message_label.setText(
        #         f"Duration shown {sgram.duration:.3f} seconds, out of {sgram.total_duration:.3f} seconds"
        #     )

    def populate_spectrogram(self, sgram: SpectrogramState, gray_cutoff):
        """Fill the spectrogram image with data"""

        vmin = (
            np.min(sgram.Sxx) + (np.max(sgram.Sxx) - np.min(sgram.Sxx)) * gray_cutoff
        )
        self.spec_img.setImage(
            sgram.Sxx.T, autoLevels=False, levels=(vmin, np.max(sgram.Sxx))
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
