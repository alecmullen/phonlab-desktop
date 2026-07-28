

import numpy as np
import pyqtgraph as pg
import sounddevice as sd
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

from core.audio_player import AudioPlayer
from ui.state.audio_wave_state import AudioWaveState
from ui.state.sgram_state import SpectrogramState
from ui.view.audio_wave_plot import AudioWavePlot
from ui.view.spectrogram_plot import SpectrogramPlot
from ui.view_model.audio_view_model import AudioViewModel


class AudioView(QWidget):
    """A single audio document with its own waveform/spectrogram display"""
    
    def __init__(self, view_model: AudioViewModel, parent=None):
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
        self.slider.valueChanged.connect(self.move_slider)

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
        self.progress_bar.setFormat("Computing %p%")
        self.progress_bar.setVisible(False)
        bottom_layout.addWidget(self.progress_bar)
        
        # ------- Layout ---------
        layout = QVBoxLayout()
        layout.addWidget(self.graphics_widget)
        layout.addWidget(self.slider)
        layout.addWidget(bottom_bar)
        self.setLayout(layout)
        
        self.plot_type = 1

        # keep the original audio found in the input file
        self.original_audio = None
        self.original_fs = None
        self.filename = None
        
        # selection time values in seconds
        self.selStart = None
        self.selEnd = None
        self.selAnchor = None
        self.mark = None

        # variables for audio playback
        self.audio_player = None
        self.is_playing = False

        # mouse interaction state
        self.ButtonDown = False
        self.init_drag = 0
        self.pan_mode = False 
        self.pan_start_x = None
        self.pan_start_view = None  
        self.pending_single_click = None
        self.click_timer = None

        # Spectrogram worker
        self.spec_worker = None
        self.freqs = None
        self.ts = None
        self.Sxx = None
        self.sgram_ready = False
        self.sgram_partial = False
        self.max_time_computed = 0.0
        self.using_mmap = False
        self.gray_cutoff = 0.55 
        self.wave_y_scale = 1.0

        self.y = None
        self.fs = None
        self.t = None
        self.miny = None
        self.maxy = None
        self.yrange = None
        self.start = 0
        self.end = 0

    def on_state_change(self, model):
        if isinstance(model, AudioWaveState):
            self.y = model.x
            self.fs = model.fs
            self.t = model.t
            self.miny = model.min_x
            self.maxy = model.max_x
            self.yrange = model.x_range

            self.update_audio_wave_view(model)
            self.load_spectrogram(model.x, model.fs)
        elif isinstance(model, SpectrogramState):
            if self.spec_plot is not None:
                self.spec_plot.populate_spectrogram(model, self.gray_cutoff)

    def load_audio(self, filename):
        """Load an audio file into this document"""
    
        self.view_model.load_audio(filename)

    def load_spectrogram(self, y, fs):
        # # Start asynchronous spectrogram computation
        # self.message_label.setText("Computing spectrogram...")  # Changed from self.parent()
        # duration = len(self.y) / self.fs
        # if duration > 60:  # longer than xx seconds
        #     chunk_duration = 10.0  # process spectrogram in longer chunks
        # else:
        #     chunk_duration = 5.0
        #
        # window_size = 0.008
        # step_size = 0.001
        # order = 13
        #
        # self.spec_worker = SpectrogramWorker(self.y, self.fs, window_size, step_size,
        #                                      order, chunk_duration)
        # self.spec_worker.progress.connect(self.on_spectrogram_progress)
        # self.spec_worker.finished.connect(self.on_spectrogram_ready)
        # self.spec_worker.error.connect(self.on_spectrogram_error)
        # self.spec_worker.start()

        self.view_model.compute_sgram(y[self.start: self.end], self.fs, self.start / self.fs, len(y) / self.fs)

    def update_audio_wave_view(self, audio_wave: AudioWaveState):
        self.selStart = self.selEnd = None  # selection start and end in seconds
        self.start = 0                      # visible window start and end in samples
        if len(audio_wave.x) > 10 * audio_wave.fs:
            self.end = 10 * audio_wave.fs         # the first 10 seconds of audio
        else:
            self.end = len(audio_wave.x) - 1
        window_size = self.end-self.start
        self.slider.setRange(0, len(audio_wave.x) - window_size - 1)
        self.slider.setValue(0)
        self.slider.setPageStep(window_size)  # one second per page step
        self.slider.setSingleStep(int(0.05 * audio_wave.fs))  # 10 milliseconds per single step
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
        s = self.start
        e = self.end

        wave_plot = AudioWavePlot()
        self.graphics_widget.addItem(wave_plot, row=row, col=col, rowspan=rowspan)
        
        wave_plot.plot_wave(self.t, audio_wave.x, s, e, audio_wave.max_x, audio_wave.min_x)
        
        return wave_plot
    
    def connect_plot_signals(self):
        """Connect mouse signals to all plots"""
        scene = self.graphics_widget.scene()
        scene.sigMouseMoved.connect(self.on_mouse_moved)
        
    def plot_wave(self, audio_wave: AudioWaveState):
        """Display waveform only"""
        self.plot_type = 1
        self.clear_plots()

        dur = (self.end - self.start) / audio_wave.fs
        totdur = len(audio_wave.x) / audio_wave.fs
        
        self.wave_plot = self.create_wave_plot(0, 0, audio_wave)
        
        self.wave_plot.setLabel('bottom', 'Time', units='s')
        self.wave_plot.getAxis('bottom').setStyle(showValues=True)
        
        self.connect_plot_signals()
        self.update_selection_box()
        self.message_label.setText(f"Duration shown {dur:.3f} seconds, out of {totdur:.3f} seconds")

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
        self.update_selection_box()

    def plot_spectrogram(self, sgram: SpectrogramState):

        if sgram.duration > 5.0:
            self.message_label.setText(
                "Zoom to a chunk of 5 seconds or shorter to see spectrogram"
            )
            return

        # if self.freqs is None:
        #     self.message_label.setText(
        #         "Spectrogram hasn't started computing, please wait..."
        #     )
        #     return
        #
        # if sgram.t[self.start] > self.max_time_computed:
        #     self.message_label.setText(
        #         f"Spectrogram not yet computed for this time range (computed up to {self.max_time_computed:.2f}s)"
        #     )
        #     return

        self.spec_plot.populate_spectrogram(sgram, self.gray_cutoff)

        # # Update message
        # if self.sgram_partial and not self.sgram_ready:
        #     self.message_label.setText(
        #         f"Showing partial spectrogram (still computing)... Duration shown {sgram.duration:.3f} seconds"
        #     )
        # else:
        #     self.message_label.setText(
        #         f"Duration shown {sgram.duration:.3f} seconds, out of {sgram.total_duration:.3f} seconds"
        #     )

    def _extract_spectrogram_window(self, s, e):
        """Extract a window from the finished spectrogram data"""
        if self.ts is None or self.Sxx is None:
            return None, None
    
        if len(self.ts) == 0 or self.Sxx.shape[1] == 0:
            return None, None
    
        sfr = np.abs(self.ts - self.t[s]).argmin()
    
        max_computed_time = self.ts[-1]
        if self.t[e] > max_computed_time:
            efr = len(self.ts) - 1
        else:
            efr = np.abs(self.ts - self.t[e]).argmin()
    
        if sfr >= efr:
            efr = min(sfr + 1, len(self.ts) - 1)
    
        ts = self.ts[sfr:efr+1]
        spec_data = self.Sxx[:, sfr:efr+1]
    
        return ts, spec_data

    def update_wave_y_range(self):
        """Update the y-axis range of the waveform plot based on scale factor"""
        if self.wave_plot:
            y_max = max(abs(self.miny), abs(self.maxy))
            scaled_max = y_max / self.wave_y_scale
            self.wave_plot.setYRange(-scaled_max, scaled_max, padding=0)

    def move_slider(self, value):
        winsize = self.end - self.start
        self.start = value
        self.end = self.start + winsize
        if self.end >= len(self.y):
            self.end = len(self.y) - 1
            self.start = self.end - winsize
        self.update_plots()

    def update_slider_page_step(self):
        """Update the slider's page step to reflect current window size"""
        window_size = self.end - self.start
        self.slider.setPageStep(window_size)
        self.slider.setMaximum(len(self.y) - 1 - window_size)
        # Ensure current value is still valid
        if self.slider.value() > self.slider.maximum():
            self.slider.setValue(self.slider.maximum())

    def go_back(self):
        size = self.end - self.start
        if self.start < size:
            self.start = 0
            self.end = size
        else:
            self.start -= size
            self.end -= size
        self.update_slider_page_step()
        self.update_plots()

    def advance(self):
        size = self.end - self.start
        if self.end + size > len(self.y) - 1:
            self.start = len(self.y) - size
            self.end = len(self.y) - 1
        else:
            self.start += size
            self.end += size
        self.update_slider_page_step()
        self.update_plots()

    def zoom_out(self, factor=2):
        size = self.end - self.start
        center = self.start + int(size / 2)
        newsize = int(size * factor)

        if newsize > len(self.y) - 1:
            self.start = 0
            self.end = len(self.y) - 1
        else:
            new_start = center - int(newsize / 2)
            new_end = center + int(newsize / 2)
            
            if new_start < 0:
                self.start = 0
                self.end = self.start + newsize
            elif new_end >= len(self.y):
                self.end = len(self.y)
                self.start = self.end - newsize
            else:
                self.start = new_start
                self.end = new_end
                
        self.update_slider_page_step()
        self.update_plots()

    def zoom_in(self, factor=2):
        size = self.end - self.start
        center = self.start + int(size / 2)
        newsize = int(size / factor)
        newsize = max(newsize, 50)
        self.start = center - int(newsize / 2)
        self.end = self.start + newsize
        self.update_slider_page_step()
        self.update_plots()

    def zoom_to_selection(self):
        if (self.selEnd is not None) and (self.selStart is not None):
            self.start = int(self.selStart * self.fs)
            self.end = int(self.selEnd * self.fs)
            self.selStart = None
            self.selEnd = None
            self.update_slider_page_step()
            self.update_plots()

    def show_all(self):
        self.start = 0
        self.end = len(self.y) - 1
        self.update_slider_page_step()  
        self.update_plots()

    def go_to_time(self, new_loc):  
        """Center the view window on a particular time (in seconds)"""
        if self.y is None or self.fs is None:
            return
        
        loc = int(new_loc * self.fs)
        size = self.end - self.start
        new_start = loc - (size // 2)
        new_end = loc + (size // 2)
        if new_start < 0:
            new_start = 0
            new_end = size
        elif new_end >= len(self.y):
            new_end = len(self.y) - 1
            new_start = new_end - size
    
        self.start = new_start
        self.end = new_end
        self.update_slider_page_step()
        self.update_plots()

        
    def recenter_on_selection(self):
        """Center the view window on the selected region without changing zoom level"""
        if self.selStart is None or self.selEnd is None:
            self.message_label.setText("No selection to center on")
            return
    
        if self.y is None or self.fs is None:
            return
    
        # Calculate the center of the selection in samples
        sel_start_samples = int(self.selStart * self.fs)
        sel_end_samples = int(self.selEnd * self.fs)
        sel_center_samples = (sel_start_samples + sel_end_samples) // 2
    
        # Calculate current window size (to maintain zoom level)
        window_size = self.end - self.start
    
        # Calculate new window bounds centered on selection
        new_start = sel_center_samples - (window_size // 2)
        new_end = sel_center_samples + (window_size // 2)
    
        # Constrain to valid range
        if new_start < 0:
            new_start = 0
            new_end = window_size
        elif new_end >= len(self.y):
            new_end = len(self.y) - 1
            new_start = new_end - window_size
    
        # Update the view
        self.start = new_start
        self.end = new_end
        self.update_slider_page_step()
        self.update_plots()
    
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
   
        if (self.selEnd is not None) and (self.selStart is not None) and x < self.selEnd and x > self.selStart:
            s = int(self.selStart * self.fs)
            e = int(self.selEnd * self.fs)
            self.play_audio(s, e)
        else:
            self.play_audio(self.start, self.end)
                        

    def update_selection_box(self):
        if self.selStart is None:
            box_left = self.start / self.fs
            xrange = 0
        else:
            box_left = self.selStart
            xrange = self.selEnd - self.selStart

        if self.spec_plot and self.plot_type == 2:
            self.spec_plot.update_selection_region(box_left, xrange)
        if self.wave_plot:
            self.wave_plot.update_selection_region(box_left, xrange)

    def update_plots(self):
        s = self.start
        e = self.end
        dur = (e - s) / self.fs
        self.slider.setValue(s)

        if self.wave_plot:
            self.wave_plot.update_wave(self.t[s:e], self.y[s:e], self.t[e])

        if self.plot_type == 2 and self.spec_plot is not None:
            if dur > 5.0:
                self.message_label.setText("Zoom to a chunk of 5 seconds or shorter to see spectrogram")
                self.spec_plot.clear()
                self.spec_plot.setXRange(self.t[s], self.t[e], padding=0)
                self.update_selection_box()
                return
            #
            # if self.freqs is None:
            #     self.message_label.setText("Spectrogram is still computing, please wait...")
            #     if self.spec_img:
            #         self.spec_img.clear()
            #     self.spec_plot.setXRange(self.t[s], self.t[e], padding=0)
            #     self.update_selection_box()
            #     return
            #
            # if self.t[s] > self.max_time_computed:
            #     self.message_label.setText(f"Spectrogram not yet computed for this time range (computed up to {self.max_time_computed:.2f}s)")
            #     if self.spec_img:
            #         self.spec_img.clear()
            #     self.spec_plot.setXRange(self.t[s], self.t[e], padding=0)
            #     self.update_selection_box()
            #     return
        
            self.view_model.compute_sgram(self.y[s:e], self.fs, s / self.fs, len(self.y) / self.fs)
        
            # if not success:
            #     self.message_label.setText("Unable to display spectrogram for this region")
            #     if self.spec_img:
            #         self.spec_img.clear()
            #

        self.update_selection_box()

    def on_mouse_moved(self, pos):
        if self.is_playing:
            return
    
        # Determine which plot the mouse is over
        status_msg = ""
    
        if self.wave_plot and self.wave_plot.sceneBoundingRect().contains(pos):
            mouse_point = self.wave_plot.vb.mapSceneToView(pos)
            x = mouse_point.x()
            status_msg = f"Cursor time: {x:.3f}s"
        
        elif self.spec_plot and self.spec_plot.sceneBoundingRect().contains(pos):
            mouse_point = self.spec_plot.vb.mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()
            status_msg = f"Cursor time: {x:.3f}s, frequency: {y:.0f} Hz"
    
        else:
            return  # Mouse not over any plot
    
        # Update vertical line positions (for both plots)
        if self.wave_plot:
            self.wave_plot.on_mouse_moved(x)
        if self.spec_plot:
            self.spec_plot.on_mouse_moved(x)

        # Handle mouse interactions (same for both plots)
        if self.ButtonDown:
            if self.init_drag > 0:
                # Start selection
                self.init_drag = -1
                self.selStart = self.selEnd = self.selAnchor = x
            elif self.init_drag == -1:
                # Continue selection - update bounds
                if x > self.selEnd:
                    self.selStart = self.selAnchor
                    self.selEnd = min(x, self.end / self.fs)
                elif self.selEnd > x > self.selStart:
                    self.selEnd = x
                elif x < self.selStart:
                    self.selStart = max(x, 0.0)
                    self.selEnd = self.selAnchor
            
                dur = self.selEnd - self.selStart
                self.update_selection_box()
                status_msg = f"Select: {self.selStart:.3f} to {self.selEnd:.3f} ({dur:.3f}s)"
                
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
                if self.is_playing:
                    return True

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
                        self.update_plots()
                
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
                    
                        self.scroll_by_fraction(scroll_fraction)
                        return True
    
        return super().eventFilter(obj, event)

    def scroll_by_fraction(self, fraction):
        """Scroll the view by a fraction of the current window size"""
        size = self.end - self.start
        scroll_amount = int(size * fraction)
    
        new_start = self.start + scroll_amount
        new_end = self.end + scroll_amount
        
        if new_start < 0:
            new_start = 0
            new_end = size
        elif new_end >= len(self.y):
            new_end = len(self.y) - 1
            new_start = new_end - size
    
        self.start = new_start
        self.end = new_end
        self.update_plots()

    def handle_mouse_press(self, scene_pos, event):
        """Handle left mouse button press"""
        clicked_plot = None
        if self.wave_plot and self.wave_plot.sceneBoundingRect().contains(scene_pos):
            clicked_plot = self.wave_plot
        elif self.spec_plot and self.spec_plot.sceneBoundingRect().contains(scene_pos):
            clicked_plot = self.spec_plot
    
        if not clicked_plot:
            return

        mouse_point = clicked_plot.vb.mapSceneToView(scene_pos)
        x = mouse_point.x()

        self.ButtonDown = True
        self.init_drag = x

    def handle_double_click(self, scene_pos):
        """Handle double-click"""
        if self.click_timer is not None:
            self.click_timer.stop()
            self.click_timer = None
            self.pending_single_click = None
    
        self.ButtonDown = False
        self.init_drag = 0

        clicked_plot = None
        if self.wave_plot and self.wave_plot.sceneBoundingRect().contains(scene_pos):
            clicked_plot = self.wave_plot
        elif self.spec_plot and self.spec_plot.sceneBoundingRect().contains(scene_pos):
            clicked_plot = self.spec_plot
            
        if not clicked_plot:
            return
            
        mouse_point = clicked_plot.vb.mapSceneToView(scene_pos)
        x = mouse_point.x()

        if (clicked_plot == self.wave_plot or clicked_plot == self.spec_plot) \
            and ((self.selEnd is not None) and (self.selStart is not None) and
                x < self.selEnd and x > self.selStart):
                self.zoom_to_selection()

    def handle_mouse_release(self, scene_pos, event):
        """Handle left mouse button release"""
        if self.ButtonDown:
            self.ButtonDown = False

            if self.init_drag == -1:
                self.init_drag = 0
                self.update_selection_box()
                if self.selStart and self.selEnd and self.selStart != self.selEnd:
                    self.play_audio(int(self.selStart * self.fs), int(self.selEnd * self.fs))
            elif self.init_drag > 0:
                self.pending_single_click = (scene_pos, event)
                if self.click_timer is not None:
                    self.click_timer.stop()
                self.click_timer = QTimer()
                self.click_timer.setSingleShot(True)
                self.click_timer.timeout.connect(self.handle_single_click)
                self.click_timer.start(250)
                self.init_drag = 0

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
        
        mouse_point = clicked_plot.vb.mapSceneToView(scene_pos)
        x = mouse_point.x()

        self.selStart = None  # clear the selection
        self.selEnd = None
        self.update_selection_box()

        self.mark = x         # remember where this click occurred
                
        
    def handle_right_click(self, scene_pos):
         pass

    def play_audio(self, s, e):
        """Play audio in a separate thread"""
        if self.audio_player and self.audio_player.isRunning():
            self.audio_player.stop()
            self.audio_player.wait()

        # stop mouse processing to make playback smoother
        self.graphics_widget.setMouseTracking(False)
        self.graphics_widget.viewport().setEnabled(False)
        self.graphics_widget.setCursor(Qt.CursorShape.WaitCursor)
    
        self.is_playing = True
        
        audio_segment = self.y[s:e]
        self.audio_player = AudioPlayer(audio_segment, self.fs)
        self.audio_player.finished.connect(self.on_playback_finished)
        self.audio_player.start()

    def stop_audio(self):
        """Stop audio playback"""
        if self.audio_player and self.audio_player.isRunning():
            self.audio_player.stop()
            self.audio_player.wait()
            self.on_playback_finished()
        elif self.is_playing:
            sd.stop()
            self.on_playback_finished()
        
    def on_playback_finished(self):
        """Called when audio playback completes"""
        self.is_playing = False
        self.graphics_widget.setMouseTracking(True)
        self.graphics_widget.viewport().setEnabled(True)
        self.graphics_widget.setCursor(Qt.CursorShape.ArrowCursor)

    def play_visible(self):
        """Play the audio currently visible in the viewport"""
        if self.y is not None and self.fs is not None:
            self.play_audio(self.start, self.end)

    def on_spectrogram_progress(self, percent, max_time_computed, freqs):
        """Called periodically as spectrogram is computed"""
        self.sgram_partial = True
        self.max_time_computed = max_time_computed
        self.freqs = freqs
        
        if self.spec_worker:
            self.using_mmap = self.spec_worker.use_mmap
            
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(percent)
        self.message_label.setText(f"Computing spectrogram... {percent}% (up to {max_time_computed:.1f}s)")
    
        if self.plot_type == 2:
            dur = (self.end - self.start) / self.fs
            if dur <= 5.0 and self.t[self.start] <= max_time_computed:
                self.update_plots()

    def on_spectrogram_ready(self, ts, freqs, Sxx):
        """Called when spectrogram computation is complete"""
        self.ts = ts
        self.freqs = freqs
        self.Sxx = Sxx
        self.sgram_ready = True
        self.sgram_partial = False
        self.using_mmap = False
        self.max_time_computed = ts[-1]
        
        self.progress_bar.setVisible(False)
        self.message_label.setText("Spectrogram ready!")

        if self.plot_type == 2:
            dur = (self.end - self.start) / self.fs
            if dur <= 5.0:
                self.update_plots()
            
    def on_spectrogram_error(self, error_msg):
        """Called when spectrogram computation fails"""
        self.message_label.setText(f"Error computing spectrogram: {error_msg}")

    def cleanup(self):
        """Clean up resources when closing document"""
        if self.audio_player and self.audio_player.isRunning():
            self.audio_player.stop()
            self.audio_player.wait()
        
        if self.spec_worker and self.spec_worker.isRunning():
            self.spec_worker.stop()
            self.spec_worker.wait(5000)
            if self.spec_worker.isRunning():
                self.spec_worker.terminate()
                self.spec_worker.wait()
