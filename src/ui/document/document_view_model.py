from dataclasses import replace

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import pyqtSlot

from core.usecase.load_audio import AudioSignal, LoadAudio
from core.usecase.play_audio import PlayAudio
from res.constants import DEFAULT_WINDOW_LENGTH
from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.base.view_model import ViewModel
from ui.document.state.audio_signal_state import AudioSignalState, to_audio_signal_state
from ui.document.state.document_window_state import DocumentWindowState
from ui.document.state.plot_layout_state import PlotLayoutState, PlotType
from ui.document.state.select_state import SelectState
from ui.document.state.status_message_state import StatusMessageState
from ui.spectrogram.spectrogram_view_model import SpectrogramViewModel
from ui.waveform.audio_wave_view_model import AudioWaveViewModel
from ui.waveform.state.audio_wave_state import to_audio_wave_state


class DocumentViewModel(ViewModel):
    def __init__(self):
        super().__init__()
        self.audio_signal_state: AudioSignalState = AudioSignalState()
        self.is_audio_playing = False
        self.select_state: SelectState = SelectState()
        self.document_window_state: DocumentWindowState = DocumentWindowState()
        self.plot_layout_state: PlotLayoutState = PlotLayoutState()

        self.audio_wave_view_model = AudioWaveViewModel()
        self.spectrogram_view_model = SpectrogramViewModel()
        self.annotation_view_model = AnnotationViewModel()

    def toggle_wave(self):
        plots = self.plot_layout_state.plots.copy()
        if PlotType.WAVEFORM not in plots:
            plots.add(PlotType.WAVEFORM)
        elif len(plots) > 1:
            plots.remove(PlotType.WAVEFORM)

        self.plot_layout_state = replace(self.plot_layout_state, plots=plots)
        self.state_changed.emit(self.plot_layout_state)

    def toggle_spectrogram(self):
        plots = self.plot_layout_state.plots.copy()
        if PlotType.SPECTROGRAM not in plots:
            plots.add(PlotType.SPECTROGRAM)
        elif len(plots) > 1:
            plots.remove(PlotType.SPECTROGRAM)

        self.plot_layout_state = replace(self.plot_layout_state, plots=plots)
        self.state_changed.emit(self.plot_layout_state)

    def toggle_annotations(self):
        plots = self.plot_layout_state.plots.copy()
        if PlotType.ANNOTATION not in plots:
            plots.add(PlotType.ANNOTATION)
        elif len(plots) > 1:
            plots.remove(PlotType.ANNOTATION)

        self.plot_layout_state = replace(self.plot_layout_state, plots=plots)
        self.state_changed.emit(self.plot_layout_state)

    def load_audio(self, filepath: str):
        @pyqtSlot(object)
        def on_success(audio_signal: AudioSignal):
            self.remove_selection()

            self.audio_signal_state = to_audio_signal_state(audio_signal)
            self.state_changed.emit(self.audio_signal_state)

            signal_end = len(audio_signal.x) - 1
            window_end = min(signal_end, DEFAULT_WINDOW_LENGTH * audio_signal.fs)
            self.document_window_state = replace(
                self.document_window_state,
                start=0,
                end=window_end,
                max_start=(signal_end - window_end),
            )
            self.update_document_window(self.document_window_state)

            msg = self.tr(
                "Duration shown {:.3f} seconds, out of {:.3f} seconds"
            ).format(
                window_end / audio_signal.fs, len(audio_signal.x) / audio_signal.fs
            )
            self.state_changed.emit(StatusMessageState(msg))

        use_case = LoadAudio(filepath)
        self.launch_use_case("load_audio", use_case, on_success, self.on_error)

    def compute_spectrogram(self):
        x, t, fs = (
            self.audio_signal_state.x,
            self.audio_signal_state.t,
            self.audio_signal_state.fs,
        )
        start, end = self.document_window_state.start, self.document_window_state.end
        self.spectrogram_view_model.compute_spectrogram(x, t, fs, start, end)

    def update_audio_waveform(self):
        start, end = self.document_window_state.start, self.document_window_state.end
        self.audio_wave_view_model.set_wave_state(
            to_audio_wave_state(self.audio_signal_state, start, end)
        )

    def play_audio(self, x: np.ndarray, fs: int):
        if self.is_audio_playing:
            self.stop_audio()

        @pyqtSlot(object)
        def on_success():
            self.is_audio_playing = False

        use_case = PlayAudio(x, fs)
        self.is_audio_playing = True
        self.launch_use_case("play_audio", use_case, on_success, self.on_error)

    def stop_audio(self):
        sd.stop()

    def update_document_window(self, document_window_state: DocumentWindowState):
        self.document_window_state = document_window_state
        self.state_changed.emit(self.document_window_state)

        self.compute_spectrogram()
        self.update_audio_waveform()

    def go_back(self):
        window_size = self.document_window_state.end - self.document_window_state.start
        self.move_start(self.document_window_state.start - window_size)

    def advance(self):
        window_size = self.document_window_state.end - self.document_window_state.start
        self.move_start(self.document_window_state.start + window_size)

    def move_start_by_fraction(self, fraction: float):
        start = self.document_window_state.start
        end = self.document_window_state.end
        scroll_amount = int((end - start) * fraction)

        self.move_start(start + scroll_amount)

    def move_start(self, new_start: int):
        start = self.document_window_state.start
        end = self.document_window_state.end
        window_size = end - start
        max_end = len(self.audio_signal_state.x) - 1

        if new_start < start:
            new_start = max(0, new_start)
            new_end = new_start + window_size
        else:
            new_end = min(max_end, new_start + window_size)
            new_start = new_end - window_size

        self.document_window_state = replace(
            self.document_window_state, start=new_start, end=new_end
        )
        self.update_document_window(self.document_window_state)

    def start_selection(self, x_pos: float):
        self.select_state = replace(
            self.select_state,
            is_selected=True,
            sel_start=x_pos,
            sel_end=x_pos,
            sel_anchor=x_pos,
        )
        self.state_changed.emit(self.select_state)

    def continue_selection(self, x_pos: float):
        sel_start = self.select_state.sel_start
        sel_end = self.select_state.sel_end

        if x_pos >= self.select_state.sel_anchor:
            sel_start = self.select_state.sel_anchor
            sel_end = min(x_pos, self.audio_signal_state.t[-1])
        elif x_pos < self.select_state.sel_anchor:
            sel_start = max(x_pos, 0.0)
            sel_end = self.select_state.sel_anchor

        self.select_state = replace(
            self.select_state, sel_start=sel_start, sel_end=sel_end
        )
        self.state_changed.emit(self.select_state)

        msg = self.tr("Select: {:.3f} to {:.3f} ({:.3f}s)").format(
            sel_start, sel_end, sel_end - sel_start
        )
        self.state_changed.emit(StatusMessageState(msg))

    def remove_selection(self):
        self.select_state = SelectState()
        self.state_changed.emit(self.select_state)

    def zoom_if_in_selection(self, x_pos: float):
        x, fs = self.audio_signal_state.x, self.audio_signal_state.fs
        max_end = len(x) - 1
        sel_start, sel_end = self.select_state.sel_start, self.select_state.sel_end
        if sel_end > x_pos > sel_start:
            start = int(sel_start * fs)
            end = int(sel_end * fs)
            window_length = end - start
            self.document_window_state = replace(
                self.document_window_state,
                start=start,
                end=end,
                max_start=max_end - window_length,
            )
            self.state_changed.emit(self.document_window_state)

            self.remove_selection()

    def center_on_selection(self):
        if not self.select_state.is_selected:
            msg = self.tr("No selection to center on")
            self.state_changed.emit(StatusMessageState(msg))
            return

        # Calculate the center of the selection in samples
        sel_start_samples = int(
            self.select_state.sel_start * self.audio_signal_state.fs
        )
        sel_end_samples = int(self.select_state.sel_end * self.audio_signal_state.fs)
        sel_center_samples = (sel_start_samples + sel_end_samples) // 2

        # Calculate new window bounds centered on selection
        window_size = self.document_window_state.end - self.document_window_state.start
        new_start = sel_center_samples - (window_size // 2)

        self.move_start(new_start)

    def zoom_out(self, factor: float = 2):
        start, end = self.document_window_state.start, self.document_window_state.end

        center = start + int((end - start) / 2)
        new_size = int((end - start) * factor)
        max_end = len(self.audio_signal_state.x) - 1

        new_end = center + int(new_size / 2)
        new_end = min(new_end, max_end)
        new_start = max(0, new_end - new_size)
        window_length = new_end - new_start

        self.document_window_state = replace(
            self.document_window_state,
            start=new_start,
            end=new_end,
            max_start=(max_end - window_length),
        )
        self.update_document_window(self.document_window_state)

    def zoom_in(self, factor: float = 2):
        start, end = self.document_window_state.start, self.document_window_state.end

        center = start + int((end - start) / 2)
        new_size = int((end - start) / factor)
        new_size = max(new_size, 50)

        new_end = center + int(new_size / 2)
        new_start = new_end - new_size

        max_end = len(self.audio_signal_state.x) - 1
        window_length = new_end - new_start

        self.document_window_state = replace(
            self.document_window_state,
            start=new_start,
            end=new_end,
            max_start=(max_end - window_length),
        )
        self.update_document_window(self.document_window_state)

    def show_all(self):
        end = len(self.audio_signal_state.x) - 1
        self.document_window_state = DocumentWindowState(start=0, end=end)
        self.update_document_window(self.document_window_state)

    def play_selected_audio(self):
        start = int(self.select_state.sel_start * self.audio_signal_state.fs)
        end = int(self.select_state.sel_end * self.audio_signal_state.fs)

        if start != end:
            section = self.audio_signal_state.x[start:end]
            self.play_audio(section, self.audio_signal_state.fs)

    def play_visible_audio(self):
        start, end = self.document_window_state.start, self.document_window_state.end

        if len(self.audio_signal_state.x) > 0:
            section = self.audio_signal_state.x[start:end]
            self.play_audio(section, self.audio_signal_state.fs)

    @pyqtSlot(object)
    def on_error(self, err):
        print(err)
