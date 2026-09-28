import pyqtgraph as pg
from PyQt6.QtCore import QPointF, Qt, pyqtSlot
from PyQt6.QtWidgets import QCheckBox, QGraphicsProxyWidget, QPushButton, QWidget
from pyqtgraph import PlotDataItem

from ui.base.state import State
from ui.common.cursor_controller import CursorController
from ui.waveform.audio_wave_view_model import AudioWaveViewModel
from ui.waveform.state.audio_wave_range_state import AudioWaveScaleState
from ui.waveform.state.audio_wave_state import AudioWaveState
from ui.waveform.state.channel_active_state import ChannelActiveState

ACTIVE_PEN = pg.mkPen("b")
INACTIVE_PEN = pg.mkPen((160, 160, 160))


class AudioWavePlot(pg.PlotItem, CursorController):
    def __init__(
        self,
        view_model: AudioWaveViewModel,
        linked_plot: pg.PlotItem | None = None,
        is_bottom_plot: bool = False,
        show_active_checkbox: bool = False,
        show_delete_button: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self.view_model = view_model
        self.view_model.subscribe(self.on_state_change)

        self.wave_curve: PlotDataItem | None = None

        if show_active_checkbox:
            # A checkbox embedded here via QGraphicsProxyWidget never
            # receives real clicks - DocumentView's event filter swallows
            # every left-click on the graphics widget before Qt's normal
            # scene dispatch ever runs. It's rendering-only: DocumentView
            # hit-tests scene_pos against active_checkbox_proxy directly and
            # calls into the view model itself, so this is never connected
            # to its own toggled signal.
            self.active_checkbox = QCheckBox(self.tr("Active"))
            self.active_checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.active_checkbox_proxy = QGraphicsProxyWidget(self)
            self.active_checkbox_proxy.setWidget(self.active_checkbox)
            self.active_checkbox_proxy.setZValue(100)
            self.getViewBox().sigResized.connect(self._reposition_checkbox)
        else:
            self.active_checkbox = None
            self.active_checkbox_proxy = None

        if show_delete_button:
            # Same rendering-only architecture as active_checkbox above: a
            # real QPushButton embedded via QGraphicsProxyWidget never
            # receives clicks because DocumentView's event filter swallows
            # every left-click on the graphics widget first. DocumentView
            # hit-tests scene_pos against delete_button_proxy directly and
            # calls into the view model, so this button's own clicked
            # signal is never connected to anything.
            self.delete_button = QPushButton("✕")
            self.delete_button.setFixedSize(18, 18)
            self.delete_button.setFlat(True)
            self.delete_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.delete_button.setToolTip(self.tr("Delete this channel"))
            self.delete_button.setStyleSheet(
                "QPushButton { border: none; color: #888; font-weight: bold; }"
                "QPushButton:hover { color: #c00; }"
            )
            self.delete_button_proxy = QGraphicsProxyWidget(self)
            self.delete_button_proxy.setWidget(self.delete_button)
            self.delete_button_proxy.setZValue(100)
            self.getViewBox().sigResized.connect(self._reposition_delete_button)
        else:
            self.delete_button = None
            self.delete_button_proxy = None

        self.setLabel("left", self.tr("Amplitude"))
        self.showGrid(x=True, y=True, alpha=0.3)
        self.getAxis("left").enableAutoSIPrefix(False)
        self.getAxis("left").setWidth(60)

        if is_bottom_plot:
            self.setLabel("bottom", self.tr("Time"), units="s")
            self.getAxis("bottom").enableAutoSIPrefix(False)
        else:
            self.getAxis("bottom").setStyle(showValues=False)

        if linked_plot is not None:
            self.getViewBox().setXLink(linked_plot)

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

        if self.active_checkbox is not None:
            self._apply_active_state(self.view_model.channel_active_state.is_active)

        self.getViewBox().menu.clear()
        self.ctrlMenu.menuAction().setVisible(False)

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
        if isinstance(model, ChannelActiveState):
            self._apply_active_state(model.is_active)

    def _apply_active_state(self, is_active: bool):
        if self.active_checkbox is not None:
            self.active_checkbox.setChecked(is_active)
        if self.wave_curve is not None:
            self.wave_curve.setPen(ACTIVE_PEN if is_active else INACTIVE_PEN)

    def _reposition_checkbox(self):
        top_left = self.mapFromScene(self.getViewBox().sceneBoundingRect().topLeft())
        self.active_checkbox_proxy.setPos(top_left.x() + 5, top_left.y() + 5)

    def _reposition_delete_button(self):
        top_right = self.mapFromScene(self.getViewBox().sceneBoundingRect().topRight())
        width = self.delete_button.width()
        self.delete_button_proxy.setPos(top_right.x() - width - 5, top_right.y() + 5)

    def plot_wave(self, audio_wave: AudioWaveState):
        limit = max(abs(audio_wave.min_x), abs(audio_wave.max_x))
        self.setYRange(-limit, limit, padding=0.05)
        self.vb.setLimits(yMin=-limit, yMax=limit)
        self.vb.setLimits(xMin=0, xMax=audio_wave.max_t)
        self.enableAutoRange(axis="y", enable=False)

        self.wave_curve = self.plot(audio_wave.t, audio_wave.x, pen=ACTIVE_PEN)
        self.wave_curve.setDownsampling(auto=True, method="peak")
        self.wave_curve.setClipToView(True)

    def update_wave(self, audio_wave: AudioWaveState):
        self.wave_curve.setData(audio_wave.t, audio_wave.x)

        # An edit (cut/paste) can change the channel's total length or
        # amplitude range - refresh the pan/zoom bounds so the display and
        # playback stay in sync (previously frozen at whatever they were
        # when the plot was first created, so e.g. audio pasted past the
        # old end of the file was audible but unreachable in the display).
        limit = max(abs(audio_wave.min_x), abs(audio_wave.max_x))
        self.vb.setLimits(yMin=-limit, yMax=limit)
        self.vb.setLimits(xMin=0, xMax=audio_wave.max_t)

        # Only reset the visible Y-range to the new default when the user
        # hasn't applied a manual amplitude zoom, so an edit doesn't clobber
        # their current zoom on every update.
        if self.view_model.audio_wave_scale_state.y_scale == 1.0:
            self.setYRange(-limit, limit, padding=0.05)

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
