import pyqtgraph as pg
from PyQt6.QtCore import QEvent, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollBar,
    QVBoxLayout,
    QWidget,
)

from ui.annotation.annotation_plot import AnnotationPlot
from ui.document.document_view_model import DocumentViewModel
from ui.document.state.audio_signal_state import AudioSignalState
from ui.document.state.document_window_state import DocumentWindowState
from ui.document.state.plot_layout_state import PlotLayoutState, PlotType
from ui.document.state.select_state import SelectState
from ui.document.state.status_message_state import StatusMessageState
from ui.spectrogram.spectrogram_plot import SpectrogramPlot
from ui.waveform.audio_wave_plot import AudioWavePlot


class DocumentView(QWidget):
    """A single audio document with its own waveform/spectrogram display"""

    def __init__(self, view_model: DocumentViewModel, parent=None):
        super().__init__(parent)
        self.view_model = view_model
        view_model.subscribe(self.on_state_change)

        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")

        # Set up PyQtGraph
        pg.setConfigOptions(antialias=True)

        # Create graphics layout widget
        self.graphics_widget = pg.GraphicsLayoutWidget()
        self.graphics_widget.viewport().installEventFilter(self)

        # Initialize plot items (will be created in plot methods)
        self.wave_plot = None
        self.spec_plot = None

        # Selection variables
        self.selection_region_wave = None
        self.selection_region_spec = None

        # ------ Slider ---------
        self.slider = QScrollBar(Qt.Orientation.Horizontal, self)

        self.slider_throttle = QTimer()
        self.slider_throttle.setInterval(15)
        self.slider_throttle.setSingleShot(True)
        self.slider_throttle.timeout.connect(self.move_start)

        self.pending_slider_value: int = 0
        self.slider.valueChanged.connect(self.on_slider_move)

        # ------- Bottom bar -------------
        bottom_bar = QWidget()
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)

        self.message_label = QLabel("")
        bottom_layout.addWidget(self.message_label)
        bottom_layout.addStretch(1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat(self.tr("Computing %p%"))
        self.progress_bar.setVisible(False)
        bottom_layout.addWidget(self.progress_bar)

        # ------- Layout ---------
        layout = QVBoxLayout()
        layout.addWidget(self.graphics_widget)
        layout.addWidget(self.slider)
        layout.addWidget(bottom_bar)
        self.setLayout(layout)

        # mouse interaction state
        self.mouse_pressed = False
        self.is_dragging = False
        self.pending_single_click = None
        self.click_timer = None

    @pyqtSlot(object)
    def on_state_change(self, model):
        if isinstance(model, AudioSignalState):
            self.reset_slider(model.fs)
            self.update_plot_layout(self.view_model.plot_layout_state)
        elif isinstance(model, SelectState):
            self.update_selection_box(model)
        elif isinstance(model, DocumentWindowState):
            self.update_slider_value(model)
        elif isinstance(model, StatusMessageState):
            self.message_label.setText(model.message)
        elif isinstance(model, PlotLayoutState):
            self.update_plot_layout(model)

    def load_audio(self, filename):
        """Load an audio file into this document"""
        self.view_model.load_audio(filename)

    def clear_plots(self):
        """Clear all current plots"""
        self.graphics_widget.clear()

        if self.wave_plot:
            self.wave_plot.clear()
            self.wave_plot = None

        self.selection_region_wave = None
        self.selection_region_spec = None

    def connect_plot_signals(self):
        """Connect mouse signals to all plots"""
        scene = self.graphics_widget.scene()
        scene.sigMouseMoved.connect(self.on_mouse_moved)

    def show_spectrogram(self, show: bool):
        self.view_model.show_spectrogram(show)

    def update_plot_layout(self, layout_state: PlotLayoutState):
        self.clear_plots()

        ordered_plots = sorted(layout_state.plots, key=lambda type: type.value)
        for i, plot_type in enumerate(ordered_plots):
            is_bottom = i == len(ordered_plots) - 1
            self.add_plot(i, plot_type, is_bottom)

        if len(layout_state.plots) == 2:
            self.graphics_widget.ci.layout.setRowStretchFactor(0, 1)
            self.graphics_widget.ci.layout.setRowStretchFactor(1, 2)
        elif len(layout_state.plots) == 3:
            self.graphics_widget.ci.layout.setRowStretchFactor(0, 1)
            self.graphics_widget.ci.layout.setRowStretchFactor(1, 1)
            self.graphics_widget.ci.layout.setRowStretchFactor(2, 1)

        self.connect_plot_signals()
        self.update_selection_box(self.view_model.select_state)

    def add_plot(self, row: int, plot_type: PlotType, is_bottom: False):
        if plot_type == PlotType.WAVEFORM:
            self.wave_plot = AudioWavePlot(
                view_model=self.view_model.audio_wave_view_model,
                is_bottom_plot=is_bottom,
            )
            self.graphics_widget.addItem(self.wave_plot, row=row, col=0)
            self.wave_plot.show()
        elif plot_type == PlotType.SPECTROGRAM:
            self.spec_plot = SpectrogramPlot(
                view_model=self.view_model.spectrogram_view_model,
                linked_plot=self.wave_plot,
                is_bottom_plot=is_bottom,
            )
            self.graphics_widget.addItem(self.spec_plot, row=row, col=0)
            self.spec_plot.show()
        elif plot_type == PlotType.ANNOTATION:
            self.annot_plot = AnnotationPlot(
                linked_plot=self.wave_plot, is_bottom_plot=is_bottom
            )
            self.graphics_widget.addItem(self.annot_plot, row=row, col=0)
            self.annot_plot.populate(self.view_model.annotation_state)
            self.annot_plot.show()

    def show_annotations(self, show: bool):
        self.view_model.show_annotations(show)

    @pyqtSlot(int)
    def on_slider_move(self, value: int):
        if not self.slider_throttle.isActive():
            self.slider_throttle.start()
        self.pending_slider_value = value

    @pyqtSlot()
    def move_start(self):
        self.view_model.move_start(self.pending_slider_value)

    def reset_slider(self, fs: int):
        self.slider.setMinimum(0)
        self.slider.setValue(0)
        self.slider.setSingleStep(int(0.05 * fs))

    def update_slider_page_step(self, doc_window: DocumentWindowState):
        """Update the slider's page step to reflect current window size"""
        window_size = doc_window.end - doc_window.start
        self.slider.setPageStep(window_size)
        self.slider.setMaximum(doc_window.max_start)

        if self.slider.value() > self.slider.maximum():
            self.slider.setValue(self.slider.maximum())

    def go_back(self):
        self.view_model.go_back()

    def advance(self):
        self.view_model.advance()

    def zoom_out(self, factor: float = 2):
        self.view_model.zoom_out(factor)

    def zoom_in(self, factor: float = 2):
        self.view_model.zoom_in(factor)

    def show_all(self):
        self.view_model.show_all()

    def recenter_on_selection(self):
        """Center the view window on the selected region without changing zoom level"""
        self.view_model.center_on_selection()

    def play_window_or_selection(self, scene_pos):
        clicked_plot = None
        if self.wave_plot and self.wave_plot.sceneBoundingRect().contains(scene_pos):
            clicked_plot = self.wave_plot
        elif self.spec_plot and self.spec_plot.sceneBoundingRect().contains(scene_pos):
            clicked_plot = self.spec_plot

        if not clicked_plot:
            return

        mouse_point = clicked_plot.getViewBox().mapSceneToView(scene_pos)
        x = mouse_point.x()

        select_state = self.view_model.select_state
        if (
            select_state.is_selected
            and select_state.sel_start < x < select_state.sel_end
        ):
            self.view_model.play_selected_audio()
        else:
            self.view_model.play_visible_audio()

    def update_selection_box(self, select_state: SelectState):
        if select_state.is_selected:
            box_left = select_state.sel_start
            xrange = select_state.sel_end - select_state.sel_start
        else:
            box_left = xrange = 0

        if self.spec_plot is not None:
            self.spec_plot.update_selection_region(box_left, xrange)
        if self.wave_plot is not None:
            self.wave_plot.update_selection_region(box_left, xrange)

    def update_slider_value(self, doc_window: DocumentWindowState):
        self.slider.setValue(doc_window.start)
        self.update_slider_page_step(doc_window)

    def on_mouse_moved(self, pos):
        # Determine which plot the mouse is over

        if self.wave_plot and self.wave_plot.sceneBoundingRect().contains(pos):
            mouse_point = self.wave_plot.vb.mapSceneToView(pos)
            x = mouse_point.x()
            status_msg = self.tr("Cursor time: {:.3f}s").format(x)

        elif self.spec_plot and self.spec_plot.sceneBoundingRect().contains(pos):
            mouse_point = self.spec_plot.getViewBox().mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()
            status_msg = self.tr("Cursor time: {:.3f}s, frequency: {:.0f} Hz").format(
                x, y
            )

        else:
            return  # Mouse not over any plot

        # Handle mouse interactions (same for both plots)
        if self.mouse_pressed:
            if not self.is_dragging:
                self.view_model.start_selection(x)
            else:
                self.view_model.continue_selection(x)
            self.is_dragging = True

        # Update status message
        self.message_label.setText(status_msg)

    def eventFilter(self, obj, event):
        """Filter mouse events from the graphics widget"""
        if obj == self.graphics_widget.viewport():
            if event.type() == QEvent.Type.MouseButtonDblClick:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.handle_double_click(event)
                    return True

            elif event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.handle_mouse_press(event)
                    return True

            elif event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.handle_mouse_release(event)
                    return True

            elif event.type() == QEvent.Type.Wheel:
                self.handle_scroll(event)
                return True
        return super().eventFilter(obj, event)

    def handle_mouse_press(self, event):
        """Handle left mouse button press"""
        scene_pos = self.graphics_widget.mapToScene(event.pos())

        clicked_plot = None
        if self.wave_plot and self.wave_plot.sceneBoundingRect().contains(scene_pos):
            clicked_plot = self.wave_plot
        elif self.spec_plot and self.spec_plot.sceneBoundingRect().contains(scene_pos):
            clicked_plot = self.spec_plot

        if not clicked_plot:
            return

        self.mouse_pressed = True

    def handle_double_click(self, event):
        """Handle double-click"""
        scene_pos = self.graphics_widget.mapToScene(event.pos())

        if self.click_timer is not None:
            self.click_timer.stop()
            self.click_timer = None
            self.pending_single_click = None

        self.mouse_pressed = False

        clicked_plot = None
        if self.wave_plot and self.wave_plot.sceneBoundingRect().contains(scene_pos):
            clicked_plot = self.wave_plot
        elif self.spec_plot and self.spec_plot.sceneBoundingRect().contains(scene_pos):
            clicked_plot = self.spec_plot

        if not clicked_plot:
            return

        mouse_point = clicked_plot.getViewBox().mapSceneToView(scene_pos)
        x = mouse_point.x()

        if clicked_plot == self.wave_plot or clicked_plot == self.spec_plot:
            self.view_model.zoom_if_in_selection(x)

    def handle_mouse_release(self, event):
        """Handle left mouse button release"""
        scene_pos = self.graphics_widget.mapToScene(event.pos())

        if self.mouse_pressed:
            self.mouse_pressed = False

            if self.is_dragging:
                self.is_dragging = False
                self.view_model.play_selected_audio()
            else:
                self.pending_single_click = (scene_pos, event)
                if self.click_timer is not None:
                    self.click_timer.stop()
                self.click_timer = QTimer()
                self.click_timer.setSingleShot(True)
                self.click_timer.timeout.connect(self.handle_single_click)
                self.click_timer.start(250)

    def handle_single_click(self):
        if self.pending_single_click is not None:
            scene_pos, _ = self.pending_single_click

            modifiers = QApplication.keyboardModifiers()
            shift_pressed = modifiers == Qt.KeyboardModifier.ShiftModifier

            if shift_pressed:
                self.set_mark(scene_pos)
            else:
                self.play_window_or_selection(scene_pos)

        self.pending_single_click = None
        self.click_timer = None

    def handle_scroll(self, event):
        angle_x = event.angleDelta().x()
        angle_y = event.angleDelta().y()
        pixel_x = event.pixelDelta().x()
        pixel_y = event.pixelDelta().y()

        modifiers = QApplication.keyboardModifiers()

        if abs(pixel_x) > 0 or abs(pixel_y) > 0:  # trackpad ??
            scroll_x = pixel_x
            scroll_y = pixel_y
            is_trackpad = True
        else:  # mouse wheel/magic mouse??
            scroll_x = angle_x / 120.0
            scroll_y = angle_y / 120.0
            is_trackpad = False

        if modifiers == Qt.KeyboardModifier.ControlModifier:
            return self.handle_control_scroll(event, scroll_y, is_trackpad)

        scroll = max(scroll_x, scroll_y, key=abs)

        if abs(scroll) > 0:
            # shift vertical scroll motion
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                return self.handle_shift_scroll(scroll)
            else:
                return self.handle_plain_scroll(scroll, is_trackpad)

    def handle_shift_scroll(self, scroll):
        if scroll > 0:
            self.zoom_in(1.05)
        else:
            self.zoom_out(1.05)
        return True

    def handle_plain_scroll(self, scroll, is_trackpad):
        if is_trackpad:
            scroll_fraction = -scroll * 0.002
        else:
            scroll_fraction = -scroll * 0.1

        self.view_model.move_start_by_fraction(scroll_fraction)
        return True

    def handle_control_scroll(self, event, scroll_y, is_trackpad):
        mouse_pos = event.position() if hasattr(event, "position") else event.pos()
        scene_pos = self.graphics_widget.mapToScene(mouse_pos.toPoint())

        delta = scroll_y

        if self.wave_plot and self.wave_plot.sceneBoundingRect().contains(scene_pos):
            self.wave_plot.adjust_y_scale(delta)
        elif self.spec_plot and self.spec_plot.sceneBoundingRect().contains(scene_pos):
            self.spec_plot.adjust_gray_scale(is_trackpad, delta)

        return True

    def set_mark(self, scene_pos):
        clicked_plot = None
        if self.wave_plot and self.wave_plot.sceneBoundingRect().contains(scene_pos):
            clicked_plot = self.wave_plot
        elif self.spec_plot and self.spec_plot.sceneBoundingRect().contains(scene_pos):
            clicked_plot = self.spec_plot

        if not clicked_plot:
            return

        self.view_model.remove_selection()

    def stop_audio(self):
        """Stop audio playback"""
        self.view_model.stop_audio()

    def play_visible(self):
        """Play the audio currently visible in the viewport"""
        self.view_model.play_visible_audio()

    def cleanup(self):
        """Clean up resources when closing document"""
        self.view_model.close_threads()
