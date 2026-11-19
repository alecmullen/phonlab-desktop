import numpy as np
import phonlab as phon
import pyqtgraph as pg
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QWidget

from res.constants import MEL_AXIS_TICKS_HZ
from ui.base.state import State
from ui.common.context_menu_hint import ContextMenuHintAction
from ui.common.document_plot import DocumentPlot
from ui.spectrogram.component.formant_settings_dialog import FormantSettingsDialog
from ui.spectrogram.component.spectrogram_settings_dialog import (
    SpectrogramSettingsDialog,
)
from ui.spectrogram.spectrogram_view_model import SpectrogramViewModel
from ui.spectrogram.state.formant_track_state import FormantTrackState
from ui.spectrogram.state.spectrogram_state import (
    FrequencyScale,
    SpectrogramState,
    SpectrogramUnavailable,
)


class SpectrogramPlot(DocumentPlot):
    def __init__(
        self,
        view_model: SpectrogramViewModel,
        linked_plot: pg.PlotItem | None = None,
        is_bottom_plot: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent, linked_plot, is_bottom_plot)

        self.view_model = view_model
        self.view_model.subscribe(self.on_state_change)

        self.setLabel("left", self.tr("Frequency"), units="Hz")
        self.getAxis("left").enableAutoSIPrefix(False)

        self.showGrid(x=True, y=True, alpha=0.3)

        self.spec_img = pg.ImageItem()
        self.addItem(self.spec_img)
        lut = pg.colormap.get("CET-L1").getLookupTable(nPts=256)[::-1]
        self.spec_img.setLookupTable(lut)

        # Where the rows of the spectrogram are on the vertical axis, in Hz or mels
        self.row_positions = np.zeros(0)
        self.is_mel = False
        self.formant_track = FormantTrackState()

        self.formant_dots = pg.ScatterPlotItem(
            pen=None, brush=pg.mkBrush("r"), size=4, pxMode=True
        )
        self.addItem(self.formant_dots, ignoreBounds=True)

        self.center_label = pg.LabelItem(
            self.unavailable_message(SpectrogramUnavailable.TOO_LONG),
            size="32pt",
            color="#A0A0A0",
        )
        self.center_label.setVisible(False)
        self.center_label.setParentItem(self.getViewBox())
        self.center_label.anchor(itemPos=(0.5, 0.5), parentPos=(0.5, 0.5))

        self.getViewBox().menu.clear()
        self.set_up_menu()
        self.ctrlMenu.menuAction().setVisible(False)

        self.plot_spectrogram(self.view_model.sgram_state)

    def set_up_menu(self):
        open_settings_action = ContextMenuHintAction(
            self.tr("Spectrogram settings..."), parent=self
        )
        open_settings_action.triggered.connect(self.open_settings_dialog)

        self.getViewBox().menu.addAction(open_settings_action)

        self.track_formants_action = ContextMenuHintAction(
            self.tr("Track formants..."), parent=self
        )
        self.track_formants_action.triggered.connect(self.open_formant_dialog)
        self.track_formants_action.setEnabled(False)
        self.getViewBox().menu.addAction(self.track_formants_action)

        clear_formants_action = ContextMenuHintAction(
            self.tr("Clear formants"), parent=self
        )
        clear_formants_action.triggered.connect(self.view_model.clear_formants)
        self.getViewBox().menu.addAction(clear_formants_action)

    @pyqtSlot(object)
    def on_state_change(self, model: State):
        if isinstance(model, SpectrogramState):
            self.plot_spectrogram(model)
        elif isinstance(model, FormantTrackState):
            self.plot_formants(model)

    def to_axis(self, hz: np.ndarray) -> np.ndarray:
        """Where frequencies (Hz) are on the vertical axis"""
        return phon.Hz_to_mel(hz) if self.is_mel else hz

    def plot_formants(self, track: FormantTrackState):
        """Draw F1-F4 as red dots; frames without a measurement are skipped."""
        self.formant_track = track
        t = np.repeat(track.sec, track.formants.shape[1])
        f = track.formants.reshape(-1)
        valid = np.isfinite(f)
        y = np.full(f.shape, np.nan)
        y[valid] = self.to_axis(f[valid])
        if self.is_mel:
            # The rows only reach so far
            valid &= (y >= self.row_positions[0]) & (y <= self.row_positions[-1])
        self.formant_dots.setData(x=t[valid], y=y[valid])

    def plot_spectrogram(self, sgram: SpectrogramState):
        self.track_formants_action.setEnabled(sgram.is_showing)
        if not sgram.is_showing and not sgram.is_loading:
            self.display_spectrogram_unavailable(sgram.unavailable)
        elif sgram.is_showing:
            self.populate_spectrogram(sgram)

    def populate_spectrogram(self, sgram: SpectrogramState) -> bool:
        """Fill the spectrogram image with data"""

        self.center_label.setVisible(False)

        self.row_positions = sgram.f
        self.is_mel = sgram.frequency_scale == FrequencyScale.MEL
        axis = self.getAxis("left")
        if self.is_mel:
            # Each row is centered on its position
            half_row = (sgram.f[1] - sgram.f[0]) / 2
            bottom, top = sgram.f[0] - half_row, sgram.f[-1] + half_row
            labeled = [
                hz
                for hz in MEL_AXIS_TICKS_HZ
                if sgram.f[0] <= phon.Hz_to_mel(hz) <= sgram.f[-1]
            ]
            places = self.to_axis(np.array(labeled, dtype=float))
            axis.setTicks([list(zip(places.tolist(), map(str, labeled)))])
            self.getViewBox().setLimits(yMin=bottom, yMax=top)
        else:
            bottom, top = sgram.f[0], sgram.f[-1]
            axis.setTicks(None)
            self.getViewBox().setLimits(yMin=0, yMax=top)
        self.getViewBox().setYRange(bottom, top)

        vmin = sgram.low_sxx + (sgram.high_sxx - sgram.low_sxx) * sgram.gray_cutoff

        self.spec_img.setImage(
            sgram.sxx_window.T,
            autoLevels=False,
            levels=(vmin, np.max(sgram.sxx_window)),
        )

        time_start = sgram.t_window[0]
        time_end = sgram.t_window[-1]

        rect = pg.QtCore.QRectF(time_start, bottom, time_end - time_start, top - bottom)
        self.spec_img.setRect(rect)

        # The dots may have been placed for another kind of axis
        self.plot_formants(self.formant_track)

        return True

    def unavailable_message(self, reason: SpectrogramUnavailable | None) -> str:
        """Tell the user which way to zoom to get a spectrogram"""
        if reason == SpectrogramUnavailable.TOO_SHORT:
            return self.tr("Zoom out to a larger chunk to see a spectrogram")
        return self.tr("Zoom in to a smaller chunk to see a spectrogram")

    def display_spectrogram_unavailable(self, reason: SpectrogramUnavailable | None):
        if self.spec_img:
            self.spec_img.clear()

        self.center_label.setText(self.unavailable_message(reason))
        self.center_label.setVisible(True)

    def adjust_gray_scale(self, is_trackpad: bool, delta: float):
        if is_trackpad:
            adjustment = delta * 0.0005
        else:
            adjustment = delta * 0.01

        self.view_model.adjust_gray_scale(adjustment)

    @pyqtSlot()
    def open_formant_dialog(self):
        settings = FormantSettingsDialog.open_formant_settings(
            self.view_model.formant_settings
        )
        if settings is not None:
            self.view_model.track_formants(settings)

    @pyqtSlot()
    def open_settings_dialog(self):
        new_settings = SpectrogramSettingsDialog.open_spectrogram_settings(
            self.view_model.spectrogram_settings
        )
        if new_settings is not None:
            self.view_model.update_settings(new_settings)
