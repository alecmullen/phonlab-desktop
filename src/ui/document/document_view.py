import pyqtgraph as pg
from PyQt6.QtCore import QPointF, Qt, QTimer, pyqtSlot
from PyQt6.QtGui import (
    QDragEnterEvent,
    QDropEvent,
    QMouseEvent,
    QResizeEvent,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QScrollBar,
    QVBoxLayout,
    QWidget,
)

from res.constants import PLOT_ROW_SPACING, PLOT_ROW_WEIGHT
from ui.annotation.annotation_plot import AnnotationPlot
from ui.base.state import State
from ui.common.context_menu_hint import ContextMenuHintAction
from ui.common.document_plot import DocumentPlot
from ui.document.component.audio_info_dialog import AudioInfoDialog
from ui.document.component.filter_dialog import FilterAudioDialog
from ui.document.component.paste_channel_dialog import PasteChannelDialog
from ui.document.component.paste_special_dialog import PasteSpecialDialog
from ui.document.component.resample_dialog import ResampleAudioDialog
from ui.document.component.scale_dialog import ScaleAudioDialog
from ui.document.document_view_model import DocumentViewModel
from ui.document.state.audio_channel_state import AudioState
from ui.document.state.audio_loaded import AudioLoaded
from ui.document.state.document_window_state import DocumentWindowState
from ui.document.state.load_progress_state import LoadProgressState
from ui.document.state.mark_state import MarkState
from ui.document.state.playback_state import PlaybackState
from ui.document.state.plot_layout_state import PlotLayoutState, PlotType
from ui.document.state.select_state import SelectState
from ui.document.state.status_message_state import StatusMessageState
from ui.main.state.audio_open_options import AudioOpenOptionsState
from ui.spectrogram.spectrogram_plot import SpectrogramPlot
from ui.waveform.audio_wave_plot import AudioWavePlot
from ui.waveform.state.audio_wave_action import (
    AudioFilterAction,
    AudioInfoAction,
    AudioResampleAction,
    AudioScaleAction,
)


class DocumentView(QWidget):
    """A single audio document with its own waveform/spectrogram display"""

    def __init__(self, view_model: DocumentViewModel, parent: QWidget | None = None):
        super().__init__(parent)
        self.view_model = view_model
        view_model.subscribe(self.on_state_change)

        # Name/path of the file this document
        self.origin_name: str | None = None
        self.origin_path: str | None = None

        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")

        # Set up PyQtGraph
        pg.setConfigOptions(antialias=True)

        # Create graphics layout widget
        self.graphics_widget = pg.GraphicsLayoutWidget()

        # Initialize plot items (will be created in plot methods)
        self.document_plots: list[DocumentPlot] = []
        self.row_weights: list[float] = []
        # Waveplots (should all be in document_plots as well)
        self.wave_plots = []
        # Track one plot to have main x-axis others link to
        self.first_plot: pg.PlotItem | None = None

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
        self.pending_single_click: QPointF | None = None
        self.click_timer = None

        # context menu
        self.context_pos: QPointF | None = None
        self.set_up_menu()

        self.setAcceptDrops(True)

    def set_up_menu(self):
        self.graphics_widget.scene().contextMenu = []

        self.zoom_to_selection_action = ContextMenuHintAction(
            self.tr("Zoom to Selection"), self.tr("Double-click"), parent=self
        )
        self.zoom_to_selection_action.triggered.connect(
            self.view_model.zoom_to_selection
        )

        self.deselect_action = ContextMenuHintAction(self.tr("Deselect"), parent=self)
        self.deselect_action.triggered.connect(self.view_model.remove_selection)

        self.set_mark_action = ContextMenuHintAction(
            self.tr("Set Mark"), self.tr("Click"), parent=self
        )
        self.set_mark_action.triggered.connect(
            lambda: (
                self.set_mark_if_in_plot(self.context_pos)
                if self.context_pos is not None
                else None
            )
        )

        self.remove_mark_action = ContextMenuHintAction(
            self.tr("Remove Mark"), parent=self
        )
        self.remove_mark_action.triggered.connect(self.view_model.remove_mark)

    def add_shared_context_menu_actions(self, view_box: pg.ViewBox):
        """Add the navigation actions (Zoom to Selection, Deselect, Set Mark,
        Remove Mark) to a plot's ViewBox menu.

        Added directly to each plot's own menu (rather than via the
        scene-wide contextMenu list) so they're present before the menu
        is ever shown.
        """
        menu = view_box.menu
        first_action = menu.actions()[0] if len(menu.actions()) > 0 else None
        menu.insertAction(first_action, self.deselect_action)
        menu.insertAction(first_action, self.set_mark_action)
        menu.insertAction(first_action, self.remove_mark_action)
        menu.aboutToShow.connect(lambda: self.sync_zoom_to_selection_action(menu))
        menu.insertSeparator(first_action)

    def sync_zoom_to_selection_action(self, menu: QMenu):
        """Put Zoom to Selection at the top of `menu` only while a selection
        exists. Adding/removing it as the menu opens (rather than toggling the
        action's visibility) makes Qt lay the rows out afresh, so it can't be
        drawn over its neighbour."""
        present = self.zoom_to_selection_action in menu.actions()
        wanted = self.view_model.select_state.is_selected
        if wanted and not present:
            menu.insertAction(self.deselect_action, self.zoom_to_selection_action)
        elif present and not wanted:
            menu.removeAction(self.zoom_to_selection_action)

    @pyqtSlot(object)
    def on_state_change(self, model: State):
        if isinstance(model, AudioLoaded):
            self.reset_slider(model.fs)
            self.update_plot_layout(self.view_model.plot_layout_state)
        elif isinstance(model, SelectState):
            self.update_selection_box(model)
        elif isinstance(model, DocumentWindowState):
            self.update_document_window(model)
        elif isinstance(model, StatusMessageState):
            self.message_label.setText(model.message)
        elif isinstance(model, PlaybackState):
            self.update_playback_cursor(model)
        elif isinstance(model, LoadProgressState):
            self.update_load_progress(model)
        elif isinstance(model, PlotLayoutState):
            self.update_plot_layout(model)
        elif isinstance(model, MarkState):
            self.update_mark(model)
        elif isinstance(model, AudioScaleAction):
            self.open_scale_dialog()
        elif isinstance(model, AudioResampleAction):
            self.open_resample_dialog()
        elif isinstance(model, AudioFilterAction):
            self.open_filter_dialog()
        elif isinstance(model, AudioInfoAction):
            self.open_audio_info()

    def load_audio(self, filename: str, options: AudioOpenOptionsState):
        """Load an audio file into this document"""
        self.view_model.load_audio(filename, options)

    def load_textgrid(self, filename: str):
        self.view_model.parse_textgrid(filename)

    def clear_plots(self):
        """Clear all current plots"""
        self.graphics_widget.clear()

        self.first_plot = None

        for plot in self.document_plots:
            del plot

        self.document_plots = []
        self.wave_plots = []

    def apply_row_heights(self):
        """Size plot rows in proportion to their weights. The bottom axis is extra
        height on the last row, outside the weighted share."""
        if not self.row_weights or len(self.row_weights) != len(self.document_plots):
            return

        layout = self.graphics_widget.ci.layout
        layout.setVerticalSpacing(PLOT_ROW_SPACING)

        _, top, _, bottom = layout.getContentsMargins()
        spacing = PLOT_ROW_SPACING * (len(self.row_weights) - 1)
        axis_height = self.document_plots[-1].getAxis("bottom").height()

        total_blankspace = top + bottom + spacing + axis_height
        available = self.graphics_widget.viewport().height() - total_blankspace
        if available <= 0:
            return

        total_weight = sum(self.row_weights)
        for row_index, weight in enumerate(self.row_weights):
            height = available * weight / total_weight
            if row_index == len(self.row_weights) - 1:
                height += axis_height
            layout.setRowFixedHeight(row_index, height)

    def connect_plot_signals(self):
        """Connect mouse signals to all plots"""
        scene = self.graphics_widget.scene()
        scene.sigMouseMoved.connect(self.on_mouse_moved)

        for plot in self.document_plots:
            scene.sigMouseMoved.connect(plot.on_mouse_moved)

    def toggle_wave(self):
        self.view_model.toggle_wave()

    def toggle_spectrogram(self):
        self.view_model.toggle_spectrogram()

    def toggle_annotations(self):
        self.view_model.toggle_annotations()

    def update_plot_layout(self, layout_state: PlotLayoutState):
        self.clear_plots()

        ordered_plots = sorted(layout_state.plots, key=lambda type: type.value)
        row = 0
        row_weights: list[float] = []
        for plot_type in ordered_plots:
            is_bottom = plot_type == ordered_plots[-1]

            plots = self.add_plot(row, plot_type, is_bottom)
            self.document_plots.extend(plots)
            if self.first_plot is None:
                self.first_plot = plots[0]

            rows_added = len(plots)
            row_weights.extend([PLOT_ROW_WEIGHT[plot_type]] * rows_added)
            row += rows_added

        self.row_weights = row_weights
        self.apply_row_heights()

        self.connect_plot_signals()
        self.update_selection_box(self.view_model.select_state)
        self.update_mark(self.view_model.mark_state)
        self.update_document_window(self.view_model.document_window_state)

    def add_plot(
        self, row: int, plot_type: PlotType, is_bottom: bool = False
    ) -> list[pg.PlotItem]:
        if plot_type == PlotType.WAVEFORM:
            return self._add_waveform_plots(row, is_bottom)
        elif plot_type == PlotType.SPECTROGRAM:
            spec_plot = SpectrogramPlot(
                view_model=self.view_model.spectrogram_view_model,
                linked_plot=self.first_plot,
                is_bottom_plot=is_bottom,
            )
            self.add_shared_context_menu_actions(spec_plot.getViewBox())
            self.graphics_widget.addItem(spec_plot, row=row, col=0)
            spec_plot.show()
            return [spec_plot]
        elif plot_type == PlotType.ANNOTATION:
            annot_plot = AnnotationPlot(
                view_model=self.view_model.annotation_view_model,
                linked_plot=self.first_plot,
                is_bottom_plot=is_bottom,
            )
            self.add_shared_context_menu_actions(annot_plot.getViewBox())
            self.graphics_widget.addItem(annot_plot, row=row, col=0)
            annot_plot.show()
            return [annot_plot]

    def _add_waveform_plots(self, row: int, is_bottom: bool) -> list[pg.PlotItem]:
        """Add one waveform row for channel 0, plus a second row for
        channel 1 when the document is stereo. Returns the plots."""
        num_channels = 2 if self.view_model.stereo_channels() is not None else 1
        self.wave_plots = []

        for idx in range(num_channels):
            wave_plot = AudioWavePlot(
                view_model=self.view_model.audio_wave_view_models[idx],
                linked_plot=self.first_plot,
                is_bottom_plot=is_bottom and idx == num_channels - 1,
                show_active_checkbox=num_channels > 1,
                show_delete_button=num_channels > 1,
            )
            wave_label = (
                self.tr("Ch {} Amplitude").format(idx + 1)
                if num_channels > 1
                else self.tr("Amplitude")
            )
            wave_plot.setLabel("left", wave_label)
            self.add_shared_context_menu_actions(wave_plot.getViewBox())
            self.graphics_widget.addItem(wave_plot, row=row + idx, col=0)
            wave_plot.show()

            self.wave_plots.append(wave_plot)
            # Must be set before creating the second wave plot, which
            # needs a valid linked_plot to x-link against.
            if idx == 0 and self.first_plot is None:
                self.first_plot = wave_plot

        return self.wave_plots

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
        self.slider.setMinimum(0)
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

    def _get_document_plot_at(self, scene_pos: QPointF) -> DocumentPlot | None:
        plot_at = None
        for plot in self.document_plots:
            if plot.sceneBoundingRect().contains(scene_pos):
                plot_at = plot

        return plot_at

    def play_window_or_selection(self, scene_pos: QPointF):
        clicked_plot = self._get_document_plot_at(scene_pos)

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
            t_range = select_state.sel_end - select_state.sel_start
        else:
            box_left = t_range = 0

        for plot in self.document_plots:
            plot.update_selection_region(box_left, t_range)

    def update_document_window(self, doc_window: DocumentWindowState):
        self.update_slider_page_step(doc_window)
        self.slider.setValue(doc_window.start)

        primary_channel = self.view_model.primary_channel()
        if primary_channel is not None and self.first_plot is not None:
            self.first_plot.getViewBox().setXRange(
                primary_channel.t[doc_window.start],
                primary_channel.t[doc_window.end],
                padding=0,
            )

    def update_mark(self, mark: MarkState):
        for plot in self.document_plots:
            plot.set_mark_position(mark.position, mark.is_set)

    def update_playback_cursor(self, playback: PlaybackState):
        if playback.is_playing:
            for plot in self.document_plots:
                plot.set_cursor_position(playback.position)

    def update_load_progress(self, progress: LoadProgressState):
        self.progress_bar.setVisible(progress.is_loading)
        if progress.is_loading:
            self.progress_bar.setRange(0, 0)  # no known percentage, just "busy"
            self.progress_bar.setFormat(self.tr("Loading full file…"))
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setFormat(self.tr("Computing %p%"))

    def map_scene_to_graphics_widget(self, pos: QPointF) -> QPointF:
        return pos - self.graphics_widget.pos().toPointF()

    def on_mouse_moved(self, pos: QPointF):
        # Determine which plot the mouse is over

        mouse_over_plot = False
        for plot in self.document_plots:
            if plot.sceneBoundingRect().contains(pos):
                mouse_over_plot = True

                mouse_point = plot.getViewBox().mapSceneToView(pos)
                x = mouse_point.x()
                y = mouse_point.y()

                if isinstance(plot, SpectrogramPlot):
                    status_msg = self.tr(
                        "Cursor time: {:.3f}s, frequency: {:.0f} Hz"
                    ).format(x, y)
                else:
                    status_msg = self.tr("Cursor time: {:.3f}s").format(x)

        if not mouse_over_plot:
            return

        if self.mouse_pressed:
            if not self.is_dragging:
                self.view_model.start_selection(x)
            else:
                self.view_model.continue_selection(x)
            self.is_dragging = True
        else:
            self.message_label.setText(status_msg)

    def mousePressEvent(self, a0: QMouseEvent | None):
        """Handle left mouse button press"""
        if a0 is None:
            return
        if a0.button() == Qt.MouseButton.RightButton:
            self.context_pos = self.map_scene_to_graphics_widget(a0.position())
            return

        scene_pos = self.map_scene_to_graphics_widget(a0.position())

        clicked_plot = self._get_document_plot_at(scene_pos)

        if clicked_plot is None:
            return

        self.mouse_pressed = True
        a0.accept()

    def mouseDoubleClickEvent(self, a0: QMouseEvent | None):
        """Handle double-click"""
        if a0 is None:
            return
        if a0.button() != Qt.MouseButton.LeftButton:
            return

        scene_pos = self.map_scene_to_graphics_widget(a0.position())

        if self.click_timer is not None:
            self.click_timer.stop()
            self.click_timer = None
            self.pending_single_click = None

        self.mouse_pressed = False

        clicked_plot = self._get_document_plot_at(scene_pos)

        if not clicked_plot:
            return

        mouse_point = clicked_plot.getViewBox().mapSceneToView(scene_pos)
        x = mouse_point.x()

        self.view_model.zoom_if_in_selection(x)
        a0.accept()

    def mouseReleaseEvent(self, a0: QMouseEvent | None):
        """Handle left mouse button release"""
        if a0 is None:
            return
        if a0.button() != Qt.MouseButton.LeftButton:
            return

        scene_pos = self.map_scene_to_graphics_widget(a0.position())

        if self.mouse_pressed:
            self.mouse_pressed = False

            if self.is_dragging:
                self.is_dragging = False
                self.view_model.play_selected_audio()
            else:
                if a0.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                    self.play_window_or_selection(scene_pos)
                else:
                    self.pending_single_click = scene_pos
                    if self.click_timer is not None:
                        self.click_timer.stop()
                    self.click_timer = QTimer()
                    self.click_timer.setSingleShot(True)
                    self.click_timer.timeout.connect(self.handle_single_click)
                    self.click_timer.start(250)

        a0.accept()

    def handle_single_click(self):
        if self.pending_single_click is not None:
            scene_pos = self.pending_single_click

            clicked_plot = self._get_document_plot_at(scene_pos)

            if clicked_plot and isinstance(clicked_plot, AnnotationPlot):
                handled = clicked_plot.handle_single_click(scene_pos)
                if handled:
                    clicked_plot = None

            if clicked_plot is not None:
                self.set_mark(scene_pos, clicked_plot)

        self.pending_single_click = None
        self.click_timer = None

    def resizeEvent(self, a0: QResizeEvent | None):
        if a0 is None:
            return
        self.apply_row_heights()
        a0.accept()

    def wheelEvent(self, a0: QWheelEvent | None):
        if a0 is None:
            return

        angle_x = a0.angleDelta().x()
        angle_y = a0.angleDelta().y()
        pixel_x = a0.pixelDelta().x()
        pixel_y = a0.pixelDelta().y()

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
            self.handle_control_scroll(a0, scroll_y, is_trackpad)
            a0.accept()
            return

        scroll = max(scroll_x, scroll_y, key=abs)

        if abs(scroll) > 0:
            # shift vertical scroll motion
            if modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.handle_shift_scroll(scroll)
            else:
                self.handle_plain_scroll(scroll, is_trackpad)

            a0.accept()

    def handle_shift_scroll(self, scroll: float):
        if scroll > 0:
            self.zoom_in(1.05)
        else:
            self.zoom_out(1.05)

    def handle_plain_scroll(self, scroll: float, is_trackpad: bool):
        if is_trackpad:
            scroll_fraction = -scroll * 0.002
        else:
            scroll_fraction = -scroll * 0.1

        self.view_model.move_start_by_fraction(scroll_fraction)

    def handle_control_scroll(
        self, event: QWheelEvent, scroll_y: float, is_trackpad: bool
    ):
        mouse_pos = event.position() if hasattr(event, "position") else event.pos()
        scene_pos = self.map_scene_to_graphics_widget(mouse_pos)

        delta = scroll_y

        plot = self._get_document_plot_at(scene_pos)
        if isinstance(plot, AudioWavePlot):
            plot.adjust_y_scale(delta)
        elif isinstance(plot, SpectrogramPlot):
            plot.adjust_gray_scale(is_trackpad, delta)

    def set_mark_if_in_plot(self, scene_pos: QPointF):
        """Set mark if position is in a document plot."""
        clicked_plot = self._get_document_plot_at(scene_pos)

        if clicked_plot:
            self.set_mark(scene_pos, clicked_plot)

    def set_mark(self, scene_pos: QPointF, clicked_plot: DocumentPlot):
        """Place a persistent mark at this time, used as the
        paste insertion point (and available for future uses)."""
        mouse_point = clicked_plot.getViewBox().mapSceneToView(scene_pos)
        x = mouse_point.x()
        self.view_model.set_mark(x)

    def stop_audio(self):
        """Stop audio playback"""
        self.view_model.stop_audio()

    def play_visible(self):
        """Play the audio currently visible in the viewport"""
        self.view_model.play_visible_audio()

    def copy_selection(self) -> AudioState | None:
        return self.view_model.copy_selection()

    def cut_selection(self) -> AudioState | None:
        return self.view_model.cut_selection()

    def paste_at_cursor(self, clip: AudioState):
        mark_position = self.view_model.mark_position_or_warn()
        if mark_position is None:
            return

        self._paste_matching_channels(mark_position, clip)

    def _paste_matching_channels(self, mark_position: float, clip: AudioState):
        """Paste `clip` at the mark, asking how to reconcile a mono/stereo
        mismatch between the document and the clip."""
        doc_is_stereo = self.view_model.stereo_channels() is not None
        if doc_is_stereo != clip.is_stereo:
            choice = PasteChannelDialog.get_channel(self, clip.is_stereo)
            if choice is None:
                return
            clip = self.view_model.reconcile_clip_for_paste(clip, choice)

        self.view_model.paste_at(mark_position, clip)

    def paste_special(self, clip: AudioState):
        mark_position = self.view_model.mark_position_or_warn()
        if mark_position is None:
            return

        new_channel_available = (
            self.view_model.stereo_channels() is None and not clip.is_stereo
        )
        choice = PasteSpecialDialog.get_choice(
            self, new_channel_available=new_channel_available
        )
        if choice is None:
            return

        if choice.reverse:
            clip = self.view_model.reversed_clip(clip)

        if not (choice.new_channel and new_channel_available):
            self._paste_matching_channels(mark_position, clip)
        elif choice.insert_silence:
            self.view_model.paste_special_new_channel_with_silence(
                choice.new_channel_idx, mark_position, clip
            )
        else:
            self.view_model.paste_special_new_channel_without_silence(
                choice.new_channel_idx, mark_position, clip
            )

    def undo(self):
        self.view_model.undo()

    def redo(self):
        self.view_model.redo()

    def dragEnterEvent(self, a0: QDragEnterEvent | None):
        if a0 is None:
            return
        mime_data = a0.mimeData()
        if mime_data is not None:
            if mime_data.hasUrls():
                a0.acceptProposedAction()
            else:
                a0.ignore()

    def dropEvent(self, a0: QDropEvent | None):
        if a0 is None:
            return
        mime_data = a0.mimeData()
        if mime_data is not None:
            path = mime_data.urls()[0].toLocalFile()
            self.load_textgrid(path)

    @pyqtSlot()
    def open_resample_dialog(self):
        primary_channel = self.view_model.primary_channel()
        if primary_channel is None:
            return

        target_fs = ResampleAudioDialog.get_target_fs(primary_channel.fs)
        if target_fs is not None:
            self.view_model.resample(target_fs)

    @pyqtSlot()
    def open_scale_dialog(self):
        if self.view_model.primary_channel() is None:
            return

        scale = ScaleAudioDialog.get_scale_value(
            applies_to_selection=self.view_model.select_state.is_selected,
            peaks_dbfs=self.view_model.peak_dbfs(),
        )
        if scale is not None:
            self.view_model.scale_audio(scale)

    @pyqtSlot()
    def open_filter_dialog(self):
        primary_channel = self.view_model.primary_channel()
        if primary_channel is None:
            return

        spec = FilterAudioDialog.get_filter_spec(primary_channel.fs)
        if spec is not None:
            self.view_model.filter_audio(spec)

    @pyqtSlot()
    def open_audio_info(self):
        origin_name = self.origin_name if self.origin_name is not None else ""
        AudioInfoDialog.show_info(
            self.view_model.primary_channel(),
            self.view_model.stereo_channels(),
            origin_name,
            self,
        )

    def cleanup(self):
        """Clean up resources when closing document"""
        self.view_model.close_threads()
