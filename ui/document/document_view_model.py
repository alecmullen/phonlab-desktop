from dataclasses import replace

from core.usecase.compute_sgram_mmap import ComputeSpectrogramMmap
import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QTimer, pyqtSlot
import phonlab as phon

from core.entity.spectrogram import Spectrogram
from core.usecase.compute_sgram import ComputeSpectrogram
from core.usecase.load_audio import AudioSignal, LoadAudio
from core.usecase.play_audio import PlayAudio
from ui.document.state.audio_wave_state import AudioWaveState, to_audio_wave_state
from ui.document.state.document_window_state import DocumentWindowState
from ui.document.state.select_state import SelectState
from ui.document.state.sgram_state import SpectrogramState
from ui.document.state.status_message_state import StatusMessageState
from ui.base.view_model import ViewModel

BUFFER_SIZE = 4800000

class DocumentViewModel(ViewModel):
    
    def __init__(self):
        super().__init__()
        self.audio_wave_state: AudioWaveState = AudioWaveState()
        self.sgram_state: SpectrogramState = SpectrogramState()
        self.is_audio_playing = False
        self.select_state: SelectState = SelectState()
        self.document_window_state: DocumentWindowState = DocumentWindowState()

        self.click_timer: QTimer | None = None

    def load_audio(self, filepath: str):
        @pyqtSlot(object)
        def on_success(audio_signal: AudioSignal):
            self.remove_selection()

            self.audio_wave_state = to_audio_wave_state(audio_signal)
            self.state_changed.emit(self.audio_wave_state)

            signal_end = len(audio_signal.x) - 1
            window_end = min(signal_end, 10 * audio_signal.fs)
            self.document_window_state = replace(
                self.document_window_state, start=0, end=window_end, max_start=(signal_end - window_end)
            )
            self.state_changed.emit(self.document_window_state)

            msg = self.tr(
                "Duration shown {:.3f} seconds, out of {:.3f} seconds"
            ).format(window_end / audio_signal.fs, len(audio_signal.x) / audio_signal.fs)
            self.state_changed.emit(StatusMessageState(msg))

        use_case = LoadAudio(filepath)
        self.launch_use_case("load_audio", use_case, on_success, self.on_error)

    def compute_spectrogram(self):
        x, fs = self.audio_wave_state.x, self.audio_wave_state.fs
        start, end = self.document_window_state.start, self.document_window_state.end

        # duration = (end - start) / fs

        # if duration > 5.0:
        #     self.sgram_state = SpectrogramState()
        #     self.state_changed.emit(self.sgram_state)
        #     return

        self.load_spectrogram_window(x, fs, start, end)

        self.load_spectrogram_buffer(x, fs, start, end)

        self.load_spectrogram_mmap(x, fs)

    def load_spectrogram_window(self, x: np.ndarray, fs: int, start: int, end: int):
        buffer_start, buffer_end = self.sgram_state.start_buffer, self.sgram_state.end_buffer

        if start >= buffer_start and end <= buffer_end:
            sfr = np.abs(self.sgram_state.t_buffer - self.audio_wave_state.t[start]).argmin()
            efr = np.abs(self.sgram_state.t_buffer - self.audio_wave_state.t[end]).argmin()

            t_window = self.sgram_state.t_buffer[sfr:efr]
            sxx_window = self.sgram_state.sxx_buffer[:,sfr:efr]

            self.sgram_state = replace(self.sgram_state, t_window=t_window, sxx_window=sxx_window)
            self.state_changed.emit(self.sgram_state)
        elif self.sgram_state.sxx_mmap is not None and self.sgram_state.t_mmap is not None:
            print("used mmap for window")

            frames_computed = self.sgram_state.frames_computed
            sfr = np.abs(self.sgram_state.t_mmap[:frames_computed] - self.audio_wave_state.t[start]).argmin()
            efr = np.abs(self.sgram_state.t_mmap[:frames_computed] - self.audio_wave_state.t[end]).argmin()

            t_window = np.array(self.sgram_state.t_mmap[sfr:efr])
            sxx_window = np.array(self.sgram_state.sxx_mmap[:,sfr:efr])

            self.sgram_state = replace(self.sgram_state, t_window=t_window, sxx_window=sxx_window)
            self.state_changed.emit(self.sgram_state)
        else:
            t, f, sxx = phon.compute_sgram(x[start:end], fs, 0.008, 0.002, 9)

            self.sgram_state = replace(self.sgram_state, t_window=t + (start / fs), sxx_window=sxx, f=f, is_showing=True)
            self.state_changed.emit(self.sgram_state)

            # @pyqtSlot(object)
            # def on_success(sgram: Spectrogram):
            #     self.sgram_state = replace(self.sgram_state, t_window=sgram.t + (start / fs), sxx_window=sgram.sxx, f=sgram.f, is_showing=True)
            #     self.state_changed.emit(self.sgram_state)

            # use_case = ComputeSpectrogram(x[start:end], fs)
            # self.launch_use_case("sgram_window", use_case, on_success, self.on_error)

    def load_spectrogram_buffer(self, x, fs, start, end):
        buffer_start = max(0, start - (BUFFER_SIZE // 2))
        buffer_end = min(len(x) - 1, start + (BUFFER_SIZE // 2))

        @pyqtSlot(object)
        def on_success(sgram: Spectrogram):
            self.sgram_state = replace(self.sgram_state, 
                t_buffer=sgram.t + (buffer_start / fs),
                sxx_buffer=sgram.sxx,
                f=sgram.f,
                start_buffer=buffer_start,
                end_buffer=buffer_end
            )
            #self.state_changed.emit(self.sgram_state)

        use_case = ComputeSpectrogram(x[buffer_start:buffer_end], fs)
        self.launch_use_case("sgram_buffer", use_case, on_success, self.on_error)

    def load_spectrogram_mmap(self, x, fs):
        @pyqtSlot(object)
        def on_success(sgram: tuple[np.memmap, np.memmap]):
            sxx_mmap, t_mmap, frames_per_sec, frames_computed = sgram
            self.sgram_state = replace(self.sgram_state, sxx_mmap=sxx_mmap, t_mmap=t_mmap, frames_per_sec=frames_per_sec, frames_computed=frames_computed)
        use_case = ComputeSpectrogramMmap(x, fs)
        self.launch_use_case("sgram_mmap", use_case, on_success, self.on_error)

    def play_audio(self, x, fs):
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
        max_end = len(self.audio_wave_state.x) - 1

        if new_start < start:
            new_start = max(0, new_start)
            new_end = new_start + window_size
        else:
            new_end = min(max_end, new_start + window_size)
            new_start = new_end - window_size

        self.document_window_state = replace(self.document_window_state, start=new_start, end=new_end)
        self.state_changed.emit(self.document_window_state)

    def start_selection(self, x_pos: float):
        self.select_state = replace(self.select_state, is_selected=True, sel_start=x_pos, sel_end=x_pos, sel_anchor=x_pos)
        self.state_changed.emit(self.select_state)

    def continue_selection(self, x_pos: float):
        sel_start = self.select_state.sel_start
        sel_end = self.select_state.sel_end

        if x_pos >= self.select_state.sel_anchor:
            sel_start = self.select_state.sel_anchor
            sel_end = min(x_pos, self.audio_wave_state.t[-1])
        elif x_pos < self.select_state.sel_start:
            sel_start = max(x_pos, 0.0)
            sel_end = self.select_state.sel_anchor

        self.select_state = replace(self.select_state, sel_start=sel_start, sel_end=sel_end)
        self.state_changed.emit(self.select_state)

        msg = self.tr("Select: {:.3f} to {:.3f} ({:.3f}s)").format(sel_start, sel_end, sel_end - sel_start)
        self.state_changed.emit(StatusMessageState(msg))

    def remove_selection(self):
        self.select_state = SelectState()
        self.state_changed.emit(self.select_state)

    def zoom_if_in_selection(self, x_pos: float):
        fs = self.audio_wave_state.fs
        sel_start, sel_end = self.select_state.sel_start, self.select_state.sel_end
        if sel_end > x_pos > sel_start:
            start = int(sel_start * fs)
            end = int(sel_end * fs)
            self.document_window_state = replace(self.document_window_state, start=start, end=end)
            self.state_changed.emit(self.document_window_state)

            self.remove_selection()
            
    def center_on_selection(self):
        if not self.select_state.is_selected:
            msg = self.tr("No selection to center on")
            self.state_changed.emit(StatusMessageState(msg))
            return

        # Calculate the center of the selection in samples
        sel_start_samples = int(self.select_state.sel_start * self.audio_wave_state.fs)
        sel_end_samples = int(self.select_state.sel_end * self.audio_wave_state.fs)
        sel_center_samples = (sel_start_samples + sel_end_samples) // 2

        # Calculate new window bounds centered on selection
        window_size = self.document_window_state.end - self.document_window_state.start
        new_start = sel_center_samples - (window_size // 2)

        self.move_start(new_start)
        
    def zoom_out(self, factor: float=2):
        start, end = self.document_window_state.start, self.document_window_state.end

        center = start + int((end - start) / 2)
        new_size = int((end - start) * factor)
        max_end = len(self.audio_wave_state.x) - 1

        new_end = center + int(new_size / 2)
        new_end = min(new_end, max_end)
        new_start = max(0, new_end - new_size)

        self.document_window_state = replace(self.document_window_state, start=new_start, end=new_end)
        self.state_changed.emit(self.document_window_state)

    def zoom_in(self, factor: float=2):
        start, end = self.document_window_state.start, self.document_window_state.end
        
        center = start + int((end - start) / 2)
        new_size = int((end - start) / factor)
        new_size = max(new_size, 50)
        
        new_end = center + int(new_size / 2)
        new_start = new_end - new_size

        self.document_window_state = replace(self.document_window_state, start=new_start, end=new_end)
        self.state_changed.emit(self.document_window_state)

    def show_all(self):
        end = len(self.audio_wave_state.x) - 1
        self.document_window_state = DocumentWindowState(start=0, end=end)
        self.state_changed.emit(self.document_window_state)
            
    def play_selected_audio(self):
        start = int(self.select_state.sel_start * self.audio_wave_state.fs)
        end = int(self.select_state.sel_end * self.audio_wave_state.fs)

        if start != end:
            section = self.audio_wave_state.x[start:end]
            self.play_audio(section, self.audio_wave_state.fs)

    def play_visible_audio(self):
        start, end = self.document_window_state.start, self.document_window_state.end

        if len(self.audio_wave_state.x) > 0:
            section = self.audio_wave_state.x[start:end]
            self.play_audio(section, self.audio_wave_state.fs)

    @pyqtSlot(object)
    def on_error(self, err):
        print(err)
