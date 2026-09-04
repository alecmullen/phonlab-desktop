import pyqtgraph as pg
from PyQt6.QtCore import QPointF, Qt, pyqtSlot
from PyQt6.QtWidgets import QWidget
from pyqtgraph import PlotDataItem

from ui.base.state import State
from ui.common.cursor_controller import CursorController
from ui.waveform.audio_wave_view_model import AudioWaveViewModel
from ui.waveform.state.audio_wave_range_state import AudioWaveScaleState
from ui.waveform.state.audio_wave_state import AudioWaveState


class AudioWavePlot(pg.PlotItem, CursorController):
    def __init__(
        self,
        view_model: AudioWaveViewModel,
        is_bottom_plot: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self.view_model = view_model
        self.view_model.subscribe(self.on_state_change)

        self.wave_curve: PlotDataItem | None = None

        self.setLabel("left", self.tr("Amplitude"))
        self.showGrid(x=True, y=True, alpha=0.3)
        self.getAxis("left").enableAutoSIPrefix(False)
        self.getAxis("left").setWidth(60)

        if is_bottom_plot:
            self.setLabel("bottom", self.tr("Time"), units="s")
            self.getAxis("bottom").enableAutoSIPrefix(False)
        else:
            self.getAxis("bottom").setStyle(showValues=False)

        self.vb.setMouseEnabled(x=False, y=False)
        self.vb.rbScaleBox.hide()
        self.enableAutoRange(axis="y", enable=False)
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

        self.mark_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(color="g", width=2, style=Qt.PenStyle.DashLine),
        )
        self.addItem(self.mark_line, ignoreBounds=True)
        self.mark_line.setVisible(False)

        if len(self.view_model.audio_wave_state.t) > 0:
            self.plot_wave(self.view_model.audio_wave_state)
            self.is_initialized = True
        else:
            self.is_initialized = False

    @pyqtSlot(object)
    def on_state_change(self, model: State):
        if isinstance(model, AudioWaveState):
            if self.is_initialized:
                self.update_wave(model)
            else:
                self.plot_wave(model)
                self.is_initialized = True
        if isinstance(model, AudioWaveScaleState):
            self.update_y_range(model.scaled_y_max)

    def plot_wave(self, audio_wave: AudioWaveState):
        limit = max(abs(audio_wave.min_x), abs(audio_wave.max_x))
        self.setYRange(-limit, limit, padding=0.05)
        self.vb.setLimits(yMin=-limit, yMax=limit)
        self.vb.setLimits(xMin=0, xMax=audio_wave.max_t)
        self.enableAutoRange(axis="y", enable=False)

        self.wave_curve = self.plot(audio_wave.t, audio_wave.x, pen="b")
        self.wave_curve.setDownsampling(auto=True, method="peak")
        self.wave_curve.setClipToView(True)
        self.setXRange(audio_wave.t[0], audio_wave.t[-1], padding=0)

    def update_wave(self, audio_wave: AudioWaveState):
        self.wave_curve.setData(audio_wave.t, audio_wave.x)
        self.setXRange(audio_wave.t[0], audio_wave.t[-1], padding=0)

    def update_selection_region(self, box_left: float, t_range: float):
        if t_range > 0:
            self.selection_region.setRegion([box_left, box_left + t_range])
            self.selection_region.setVisible(True)
        else:
            self.selection_region.setVisible(False)

    def adjust_y_scale(self, delta: float):
        self.view_model.update_wave_y_range(delta)

    def update_y_range(self, scaled_y_max: float):
        self.setYRange(-scaled_y_max, scaled_y_max, padding=0)

    @pyqtSlot(object)
    def on_mouse_moved(self, pos: QPointF):
        if self.has_cursor_control:
            x = self.getViewBox().mapSceneToView(pos).x()
            self.cursor_line.setPos(x)

    def set_cursor_position(self, x: float):
        self.remove_cursor_control()
        self.cursor_line.setPos(x)

    def set_mark_position(self, x: float, visible: bool):
        self.mark_line.setPos(x)
        self.mark_line.setVisible(visible)

    def clear(self):
        self.wave_curve = None
