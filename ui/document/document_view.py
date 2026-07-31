import pyqtgraph as pg
from PyQt6.QtCore import QEvent, Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollBar,
    QVBoxLayout,
    QWidget,
)

from ui.document.state.audio_wave_state import AudioWaveState
from ui.document.state.document_window_state import DocumentWindowState
from ui.document.state.select_state import SelectState
from ui.document.state.sgram_state import SpectrogramState
from ui.document.state.status_message_state import StatusMessageState
from ui.document.component.audio_wave_plot import AudioWavePlot
from ui.document.component.spectrogram_plot import SpectrogramPlot
from ui.document.document_view_model import DocumentViewModel


class DocumentView(QWidget):
    """A single audio document with its own waveform/spectrogram display"""
    
    def __init__(self, view_model: DocumentViewModel, parent=None):
        super().__init__(parent)
        self.view_model = view_model
        view_model.subscribe(self.on_state_change)

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

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
        self.slider.valueChanged.connect(self.view_model.move_start)

        # ------- Bottom bar -------------
        bottom_bar = QWidget()
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(0,0,0,0)
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

        self.plot_type = 1

        # mouse interaction state
        self.mouse_pressed = False
        self.is_dragging = False
        self.pending_single_click = None
        self.click_timer = None

        self.gray_cutoff = 0.55
        self.wave_y_scale = 1.0

    def on_state_change(self, model):
        if isinstance(model, AudioWaveState):
            self.load_audio_wave_view(model)
            self.view_model.compute_spectrogram()
        elif isinstance(model, SpectrogramState):
            if self.spec_plot is not None:
                self.plot_spectrogram(model)
        elif isinstance(model, SelectState):
            self.update_selection_box(model)
        elif isinstance(model, DocumentWindowState):
            self.update_document_window(model)
        elif isinstance(model, StatusMessageState):
            self.message_label.setText(model.message)

    def load_audio(self, filename):
        """Load an audio file into this document"""
        self.view_model.load_audio(filename)

    def load_audio_wave_view(self, audio_wave: AudioWaveState):
        self.reset_slider(audio_wave.fs)
        self.plot_wave(audio_wave)

    def clear_plots(self):
        """Clear all current plots"""
        self.graphics_widget.clear()

        if self.wave_plot:
            self.wave_plot.clear()
            self.wave_plot = None

        self.selection_region_wave = None
        self.selection_region_spec = None

    def create_wave_plot(self, row, col, audio_wave: AudioWaveState, rowspan=1):
        """Create a waveform plot at the specified position"""
        start, end = self.view_model.document_window_state.start, self.view_model.document_window_state.end

        wave_plot = AudioWavePlot()
        self.graphics_widget.addItem(wave_plot, row=row, col=col, rowspan=rowspan)
        
        wave_plot.plot_wave(audio_wave.t, audio_wave.x, start, end, audio_wave.max_x, audio_wave.min_x)
        
        return wave_plot
    
    def connect_plot_signals(self):
        """Connect mouse signals to all plots"""
        scene = self.graphics_widget.scene()
        scene.sigMouseMoved.connect(self.on_mouse_moved)
        
    def plot_wave(self, audio_wave: AudioWaveState | None = None):
        """Display waveform only"""
        if audio_wave is None:
            audio_wave = self.view_model.audio_wave_state

        self.plot_type = 1
        self.clear_plots()
        
        self.wave_plot = self.create_wave_plot(0, 0, audio_wave)
        
        self.wave_plot.setLabel('bottom', self.tr('Time'), units='s')
        self.wave_plot.getAxis('bottom').setStyle(showValues=True)
        
        self.connect_plot_signals()
        self.update_selection_box(self.view_model.select_state)

    def plot_wave_sgram(self):
        """Display waveform and spectrogram"""
        self.plot_type = 2
        self.clear_plots()
    
        self.wave_plot = self.create_wave_plot(row=0, col=0, audio_wave=self.view_model.audio_wave_state)
    
        self.wave_plot.getAxis('bottom').setStyle(showValues=False)

        self.wave_plot.getAxis('left').setWidth(60)

        self.spec_plot = SpectrogramPlot(linked_plot=self.wave_plot)
        self.graphics_widget.addItem(self.spec_plot, row=1, col=0)
        self.plot_spectrogram(self.view_model.sgram_state)
        self.spec_plot.show()

        self.graphics_widget.ci.layout.setRowStretchFactor(0, 1)
        self.graphics_widget.ci.layout.setRowStretchFactor(1, 2)

        self.connect_plot_signals()
        self.update_selection_box(self.view_model.select_state)

    def plot_spectrogram(self, sgram: SpectrogramState):
        if not sgram.is_showing:
            self.spec_plot.clear()
            self.message_label.setText(self.tr("Zoom to a chunk of 5 seconds or shorter to see spectrogram"))
        else:
            self.spec_plot.populate_spectrogram(sgram, self.gray_cutoff)

    def update_wave_y_range(self):
        """Update the y-axis range of the waveform plot based on scale factor"""
        max_x, min_x = self.view_model.audio_wave_state.max_x, self.view_model.audio_wave_state.min_x
        if self.wave_plot:
            y_max = max(abs(min_x), abs(max_x))
            scaled_max = y_max / self.wave_y_scale
            self.wave_plot.setYRange(-scaled_max, scaled_max, padding=0)
            
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

    def zoom_out(self, factor: float=2):
        self.view_model.zoom_out(factor)

    def zoom_in(self, factor: float=2):
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
            
        mouse_point = clicked_plot.vb.mapSceneToView(scene_pos)
        x = mouse_point.x()

        select_state = self.view_model.select_state
        if select_state.is_selected and select_state.sel_start < x < select_state.sel_end:
            self.view_model.play_selected_audio()
        else:
            self.view_model.play_visible_audio()
                        

    def update_selection_box(self, select_state: SelectState):
        if select_state.is_selected:
            box_left = select_state.sel_start
            xrange = select_state.sel_end - select_state.sel_start
        else:
            box_left = xrange = 0

        if self.spec_plot and self.plot_type == 2:
            self.spec_plot.update_selection_region(box_left, xrange)
        if self.wave_plot:
            self.wave_plot.update_selection_region(box_left, xrange)
        
    def update_document_window(self, doc_window: DocumentWindowState):
        start, end = doc_window.start, doc_window.end
        t, x = self.view_model.audio_wave_state.t, self.view_model.audio_wave_state.x
        self.slider.setValue(start)

        if self.wave_plot:
            self.wave_plot.update_wave(t[start:end], x[start:end], t[end])

        self.view_model.compute_spectrogram()
        self.update_slider_page_step(doc_window)

    def update_grayscale(self):
        self.plot_spectrogram(self.view_model.sgram_state)

    def on_mouse_moved(self, pos):
        # Determine which plot the mouse is over

        if self.wave_plot and self.wave_plot.sceneBoundingRect().contains(pos):
            mouse_point = self.wave_plot.vb.mapSceneToView(pos)
            x = mouse_point.x()
            status_msg = self.tr("Cursor time: {:.3f}s").format(x)
        
        elif self.spec_plot and self.spec_plot.sceneBoundingRect().contains(pos):
            mouse_point = self.spec_plot.vb.mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()
            status_msg = self.tr("Cursor time: {:.3f}s, frequency: {:.0f} Hz").format(x, y)

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
                    if self.click_timer is not None:
                        self.click_timer.stop()
                        self.click_timer = None
                        self.pending_single_click = None
                    scene_pos = self.graphics_widget.mapToScene(event.pos())
                    self.handle_double_click(scene_pos)
                    return True

            elif event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    scene_pos = self.graphics_widget.mapToScene(event.pos())
                    self.handle_mouse_press(scene_pos, event)
                    return True
                
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton:
                    scene_pos = self.graphics_widget.mapToScene(event.pos())
                    self.handle_mouse_release(scene_pos, event)
                    return True
                
            elif event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.RightButton:
                    scene_pos = self.graphics_widget.mapToScene(event.pos())
                    self.handle_right_click(scene_pos)
                    return True
                
            elif event.type() == QEvent.Type.Wheel:

                angle_x = event.angleDelta().x()
                angle_y = event.angleDelta().x()
                pixel_x = event.pixelDelta().x()
                pixel_y = event.pixelDelta().x()
            
                modifiers = QApplication.keyboardModifiers()
            
                if abs(pixel_x) > 0 or abs(pixel_y) > 0:   # trackpad ??
                    scroll_x = pixel_x
                    scroll_y = pixel_y
                    is_trackpad = True
                else:                                      # mouse wheel/magic mouse??
                    scroll_x = angle_x / 120.0
                    scroll_y = angle_y / 120.0
                    is_trackpad = False

                if modifiers == Qt.KeyboardModifier.ControlModifier:
                    mouse_pos = event.position() if hasattr(event, 'position') else event.pos()
                    scene_pos = self.graphics_widget.mapToScene(mouse_pos.toPoint())
                
                    over_wave = False
                    over_spec = False
                
                    if self.wave_plot and self.wave_plot.sceneBoundingRect().contains(scene_pos):
                        over_wave = True
                    elif self.spec_plot and self.spec_plot.sceneBoundingRect().contains(scene_pos):
                        over_spec = True
                
                    delta = scroll_y
                
                    if over_wave:
                        if delta > 0:
                            self.wave_y_scale *= 1.05
                        else:
                            self.wave_y_scale *= 0.95
                    
                        self.wave_y_scale = max(0.1, min(10.0, self.wave_y_scale))
                        self.update_wave_y_range()
                
                    elif over_spec:   # adjust gray scale
                        if is_trackpad:
                            adjustment = delta * 0.0005
                        else:
                            adjustment = delta * 0.01
                    
                        self.gray_cutoff += adjustment
                        self.gray_cutoff = max(0.0, min(0.7, self.gray_cutoff))
                        self.update_grayscale()
                
                    return True
                
                if abs(scroll_x) > abs(scroll_y):    # horizontal motion
                    #if is_trackpad:    
                    #    scroll_fraction = -scroll_x * 0.002
                    #    self.scroll_by_fraction(scroll_fraction)
                    #else:
                    #    scroll_fraction = -scroll_x * 0.1
                    #    self.scroll_by_fraction(scroll_fraction)
                    return True

                elif abs(scroll_y) > 0:              # vertical motion
                    # shift vertical scroll motion
                    if modifiers == Qt.KeyboardModifier.ShiftModifier:
                        if scroll_y > 0:
                            self.zoom_in(1.05)
                        else:
                            self.zoom_out(1.05)
                    # plain vertical scroll motion
                    else:
                        if is_trackpad:
                            scroll_fraction = -scroll_y * 0.002
                        else:
                            scroll_fraction = -scroll_y * 0.1
                    
                        self.view_model.move_start_by_fraction(scroll_fraction)
                        return True
    
        return super().eventFilter(obj, event)

    def handle_mouse_press(self, scene_pos, event):
        """Handle left mouse button press"""
        clicked_plot = None
        if self.wave_plot and self.wave_plot.sceneBoundingRect().contains(scene_pos):
            clicked_plot = self.wave_plot
        elif self.spec_plot and self.spec_plot.sceneBoundingRect().contains(scene_pos):
            clicked_plot = self.spec_plot
    
        if not clicked_plot:
            return

        self.mouse_pressed = True

    def handle_double_click(self, scene_pos):
        """Handle double-click"""
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
            
        mouse_point = clicked_plot.vb.mapSceneToView(scene_pos)
        x = mouse_point.x()

        if clicked_plot == self.wave_plot or clicked_plot == self.spec_plot:
            self.view_model.zoom_if_in_selection(x)

    def handle_mouse_release(self, scene_pos, event):
        """Handle left mouse button release"""
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
            scene_pos,_ = self.pending_single_click

            modifiers = QApplication.keyboardModifiers()
            shift_pressed = modifiers == Qt.KeyboardModifier.ShiftModifier
    
            if shift_pressed:
                self.set_mark(scene_pos)
            else:
                self.play_window_or_selection(scene_pos)
                     
        self.pending_single_click = None
        self.click_timer = None

    def set_mark(self, scene_pos):
        
        clicked_plot = None
        if self.wave_plot and self.wave_plot.sceneBoundingRect().contains(scene_pos):
            clicked_plot = self.wave_plot
        elif self.spec_plot and self.spec_plot.sceneBoundingRect().contains(scene_pos):
            clicked_plot = self.spec_plot
            
        if not clicked_plot:
            return

        self.view_model.remove_selection()
        
    def handle_right_click(self, scene_pos):
         pass

    def stop_audio(self):
        """Stop audio playback"""
        self.view_model.stop_audio()

    def play_visible(self):
        """Play the audio currently visible in the viewport"""
        self.view_model.play_visible_audio()

    def cleanup(self):
        """Clean up resources when closing document"""
        self.view_model.close_threads()
