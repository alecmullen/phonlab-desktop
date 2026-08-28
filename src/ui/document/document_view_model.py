from dataclasses import replace

import numpy as np
import phonlab as phon
from PyQt6.QtCore import QTimer, pyqtSlot

from core.edit_audio.entity.edit_command import EditCommand
from core.edit_audio.load_audio_from_samples import LoadAudioFromSamples
from core.edit_audio.resample import resample_signal
from core.load_audio.entity.audio_document import AudioDocument
from core.load_audio.entity.audio_open_options import AudioOpenOptions
from core.load_audio.entity.audio_signal import AudioSignal
from core.load_audio.load_audio import LoadAudio
from core.load_audio.prep_channel import prep_channel
from core.play_audio.audio_player import AudioPlayer
from core.play_audio.entity.playback_poll import PlaybackPoll
from core.spectrogram.compute_sgram import ComputeSpectrogram
from core.spectrogram.compute_sgram_mmap import ComputeSpectrogramMmap
from core.spectrogram.entity.spectrogram import Spectrogram
from core.spectrogram.entity.spectrogram_mmap import SpectrogramMmap
from res.constants import MAX_SGRAM_LENGTH, MAX_UNDO_HISTORY
from ui.base.view_model import ViewModel
from ui.document.state.audio_wave_state import AudioWaveState, to_audio_wave_state
from ui.document.state.document_window_state import DocumentWindowState
from ui.document.state.load_progress_state import LoadProgressState
from ui.document.state.mark_state import MarkState
from ui.document.state.playback_state import PlaybackState
from ui.document.state.plot_layout_state import PlotLayoutState
from ui.document.state.select_state import SelectState
from ui.document.state.sgram_state import SpectrogramState
from ui.document.state.status_message_state import StatusMessageState

LATENCY_WARNING_THRESHOLD_S = 0.1  # audacity's own reference for "robust" latency


class DocumentViewModel(ViewModel):
    def __init__(self):
        super().__init__()
        self.audio_wave_state: AudioWaveState = AudioWaveState()
        self.raw_wave_state: AudioWaveState = AudioWaveState()
        self.audio_document: AudioDocument | None = None
        self.sgram_state: SpectrogramState = SpectrogramState()
        self.is_audio_playing = False
        self.select_state: SelectState = SelectState()
        self.document_window_state: DocumentWindowState = DocumentWindowState()
        self.plot_layout_state: PlotLayoutState = PlotLayoutState()
        self.playback_state = PlaybackState()
        self.mark_state: MarkState = MarkState()

        self.undo_stack: list[EditCommand] = []
        self.redo_stack: list[EditCommand] = []
        self._buffer_generation = 0

        self.click_timer: QTimer | None = None

        self.audio_player = AudioPlayer()

    def _apply_audio_document(
        self, audio_document: AudioDocument, initialize_window: bool, is_loading: bool
    ):
        # This replaces audio_wave_state/raw_wave_state just like
        # _replace_raw_buffer does (e.g. the preview -> full-file swap), so
        # it needs the same staleness guard for any spectrogram job still
        # in flight against the buffer being replaced.
        self._buffer_generation += 1
        self.audio_document = audio_document
        audio_signal = audio_document.channels[audio_document.primary_channel]

        if audio_document.original_channels is not None:
            raw_signal = AudioSignal(
                audio_document.original_channels[audio_document.primary_channel],
                audio_document.original_fs,
            )
        else:
            # Preview yield: the unprocessed file hasn't been read yet,
            # so fall back to the prepped preview signal for display.
            raw_signal = audio_signal

        if initialize_window:
            self.remove_selection()

        self.audio_wave_state = to_audio_wave_state(audio_signal)
        self.raw_wave_state = to_audio_wave_state(raw_signal)
        self.state_changed.emit(self.audio_wave_state)

        signal_end = len(audio_signal.x) - 1
        window_end = min(signal_end, MAX_SGRAM_LENGTH * audio_signal.fs)
        if initialize_window:
            # Nothing has loaded past the preview yet, so scrolling is
            # capped to what's currently in memory.
            self.document_window_state = replace(
                self.document_window_state,
                start=0,
                end=window_end,
                max_start=(signal_end - window_end),
            )
        else:
            # Keep whatever the user is currently looking at; just
            # widen how far they're now allowed to scroll.
            self.document_window_state = replace(
                self.document_window_state,
                max_start=(signal_end - window_end),
            )
        self.state_changed.emit(self.document_window_state)

        self.state_changed.emit(LoadProgressState(is_loading=is_loading))

        if not is_loading:
            shown = (
                self.document_window_state.end - self.document_window_state.start
            )
            msg = self.tr(
                "Duration shown {:.3f} seconds, out of {:.3f} seconds"
            ).format(shown / audio_signal.fs, len(audio_signal.x) / audio_signal.fs)
            self.state_changed.emit(StatusMessageState(msg))

    def load_audio(self, filepath: str, options: AudioOpenOptions):
        # LoadAudio yields twice: a fast preview of the first window, then
        # the fully loaded file once it's ready
        @pyqtSlot(object)
        def on_success(audio_document: AudioDocument):
            self._apply_audio_document(
                audio_document, initialize_window=audio_document.is_preview, is_loading=audio_document.is_preview
            )

        use_case = LoadAudio(
            filepath,
            target_fs=options.target_fs,
            channel_mode=options.channel_mode,
            retained_channels=options.retained_channels,
            primary_channel=options.primary_channel,
        )
        self.launch_use_case("load_audio", use_case, on_success, self.on_error)

    def load_from_samples(self, x: np.ndarray, fs: int, target_fs: int):
        @pyqtSlot(object)
        def on_success(audio_document: AudioDocument):
            self._apply_audio_document(
                audio_document, initialize_window=True, is_loading=False
            )

        use_case = LoadAudioFromSamples(x, fs, target_fs)
        self.launch_use_case("load_audio", use_case, on_success, self.on_error)

    def show_spectrogram(self, show: bool):
        self.plot_layout_state = replace(self.plot_layout_state, is_spectrogram=show)
        self.state_changed.emit(self.plot_layout_state)
        if show:
            self.compute_spectrogram()

    def compute_spectrogram(self):
        if not self.plot_layout_state.is_spectrogram:
            return

        x, fs = self.audio_wave_state.x, self.audio_wave_state.fs
        start, end = self.document_window_state.start, self.document_window_state.end

        if (end - start) / fs > MAX_SGRAM_LENGTH:
            self.sgram_state = replace(self.sgram_state, is_showing=False)
            self.state_changed.emit(self.sgram_state)
            return

        self.load_spectrogram_window(x, fs, start, end)
        self.load_spectrogram_mmap(x, fs)

    def load_spectrogram_window(self, x: np.ndarray, fs: int, start: int, end: int):
        if (
            self.sgram_state.sxx_mmap is not None
            and self.sgram_state.t_mmap is not None
            and self.sgram_state.samples_computed > end
        ):
            frames_computed = self.sgram_state.frames_computed
            sfr = np.abs(
                self.sgram_state.t_mmap[:frames_computed]
                - self.audio_wave_state.t[start]
            ).argmin()
            efr = np.abs(
                self.sgram_state.t_mmap[:frames_computed] - self.audio_wave_state.t[end]
            ).argmin()

            t_window = np.array(self.sgram_state.t_mmap[sfr:efr])
            sxx_window = np.array(self.sgram_state.sxx_mmap[:, sfr:efr])

            self.sgram_state = replace(
                self.sgram_state,
                t_window=t_window,
                sxx_window=sxx_window,
                is_showing=True,
            )
            self.state_changed.emit(self.sgram_state)
        else:
            t, f, sxx = phon.compute_sgram(x[start:end], fs, 0.008, 0.003, 9)

            self.sgram_state = replace(
                self.sgram_state,
                t_window=t + (start / fs),
                sxx_window=sxx,
                f=f,
                is_showing=True,
            )
            self.state_changed.emit(self.sgram_state)

            generation = self._buffer_generation

            @pyqtSlot(object)
            def on_success(sgram: Spectrogram):
                if generation != self._buffer_generation:
                    return  # stale result computed against a since-replaced buffer
                self.sgram_state = replace(
                    self.sgram_state,
                    t_window=sgram.t + (start / fs),
                    sxx_window=sgram.sxx,
                    f=sgram.f,
                    is_showing=True,
                )
                self.state_changed.emit(self.sgram_state)

            use_case = ComputeSpectrogram(x[start:end], fs)
            self.launch_use_case("sgram_window", use_case, on_success, self.on_error)

    def load_spectrogram_mmap(self, x, fs):
        if self.sgram_state.sxx_mmap is None or self.sgram_state.t_mmap is None:

            generation = self._buffer_generation

            @pyqtSlot(object)
            def on_success(sgram: SpectrogramMmap):
                if generation != self._buffer_generation:
                    return  # stale result computed against a since-replaced buffer
                self.sgram_state = replace(
                    self.sgram_state,
                    sxx_mmap=sgram.sxx_mmap,
                    t_mmap=sgram.t_mmap,
                    frames_per_sec=sgram.frames_per_sec,
                    frames_computed=sgram.frames_computed,
                    samples_computed=sgram.samples_computed,
                )

            use_case = ComputeSpectrogramMmap(x, fs)
            self.launch_use_case(
                "sgram_mmap", use_case, on_success, self.on_error, only_once=True
            )

    def play_audio(self, x: np.ndarray, fs: int, start: int):
        self.stop_audio()

        @pyqtSlot(object)
        def on_poll(playback_poll: PlaybackPoll):
            high_latency = playback_poll.latency > LATENCY_WARNING_THRESHOLD_S

            if high_latency and not self.playback_state.high_latency:
                msg = self.tr(
                    "System audio latency is a little long ({:.0f} ms). Consider using a different audio device."
                ).format(playback_poll.latency  * 1000)
                self.state_changed.emit(StatusMessageState(msg))

            self.playback_state = PlaybackState(playback_poll.is_playing, playback_poll.current_time, high_latency)
            self.state_changed.emit(self.playback_state)

        self.audio_player.playback_poll.connect(on_poll)
        self.audio_player.play(x, fs, start / self.audio_wave_state.fs)

    def stop_audio(self):
        self.audio_player.stop()    

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

        self.document_window_state = replace(
            self.document_window_state, start=new_start, end=new_end
        )
        self.state_changed.emit(self.document_window_state)

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
            sel_end = min(x_pos, self.audio_wave_state.t[-1])
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
        x, fs = self.audio_wave_state.x, self.audio_wave_state.fs
        max_end = len(x) - 1
        sel_start, sel_end = self.select_state.sel_start, self.select_state.sel_end
        if sel_end > x_pos > sel_start:
            start = int(sel_start * fs)
            end = int(sel_end * fs)
            window_length = end - start
            self.document_window_state = replace(
                self.document_window_state, start=start, end=end, max_start=max_end - window_length
            )
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

    def zoom_out(self, factor: float = 2):
        start, end = self.document_window_state.start, self.document_window_state.end

        center = start + int((end - start) / 2)
        new_size = int((end - start) * factor)
        max_end = len(self.audio_wave_state.x) - 1

        new_end = center + int(new_size / 2)
        new_end = min(new_end, max_end)
        new_start = max(0, new_end - new_size)
        window_length = new_end - new_start

        self.document_window_state = replace(
            self.document_window_state, start=new_start, end=new_end, max_start=(max_end - window_length)
        )
        self.state_changed.emit(self.document_window_state)

    def zoom_in(self, factor: float = 2):
        start, end = self.document_window_state.start, self.document_window_state.end

        center = start + int((end - start) / 2)
        new_size = int((end - start) / factor)
        new_size = max(new_size, 50)

        new_end = center + int(new_size / 2)
        new_start = new_end - new_size

        max_end = len(self.audio_wave_state.x) - 1
        window_length = new_end - new_start

        self.document_window_state = replace(
            self.document_window_state, start=new_start, end=new_end, max_start=(max_end - window_length)
        )
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
            self.play_audio(section, self.audio_wave_state.fs, start=start)

    def play_visible_audio(self):
        start, end = self.document_window_state.start, self.document_window_state.end

        if len(self.audio_wave_state.x) > 0:
            section = self.audio_wave_state.x[start:end]
            self.play_audio(section, self.audio_wave_state.fs, start=start)

    def set_mark(self, x_pos: float):
        self.mark_state = MarkState(position=x_pos, is_set=True)
        self.state_changed.emit(self.mark_state)

    def _raw_buffer_ready(self) -> bool:
        if self.audio_document is None or self.audio_document.original_channels is None:
            self.state_changed.emit(
                StatusMessageState(self.tr("Audio is still loading, please wait."))
            )
            return False
        return True

    def _replace_raw_buffer(self, new_raw_x: np.ndarray) -> bool:
        if len(new_raw_x) == 0:
            self.state_changed.emit(
                StatusMessageState(self.tr("Cannot remove entire selection"))
            )
            return False

        raw_fs = self.raw_wave_state.fs
        self.raw_wave_state = to_audio_wave_state(AudioSignal(new_raw_x, raw_fs))
        if self.audio_document.original_channels is not None:
            self.audio_document.original_channels[
                self.audio_document.primary_channel
            ] = new_raw_x

        prepped = prep_channel(new_raw_x, raw_fs, self.audio_wave_state.fs)
        new_prepped_x, new_prepped_fs = prepped.x, prepped.fs
        self.audio_document.channels[self.audio_document.primary_channel] = prepped

        signal_end = max(0, len(new_prepped_x) - 1)
        window_size = self.document_window_state.end - self.document_window_state.start
        new_start = min(self.document_window_state.start, max(0, signal_end - window_size))
        new_end = min(new_start + window_size, signal_end)
        self.document_window_state = replace(
            self.document_window_state,
            start=new_start,
            end=new_end,
            max_start=max(0, signal_end - window_size),
        )

        # Invalidate stale spectrogram jobs/results computed against the old
        # buffer before triggering any recompute against the new one.
        self._buffer_generation += 1
        self.close_thread("sgram_mmap")
        self.close_thread("sgram_window")
        self.sgram_state = SpectrogramState()

        self.audio_wave_state = to_audio_wave_state(AudioSignal(new_prepped_x, new_prepped_fs))
        self.state_changed.emit(self.audio_wave_state)
        self.state_changed.emit(self.document_window_state)

        self.remove_selection()
        self.mark_state = MarkState()
        self.state_changed.emit(self.mark_state)
        return True

    def _remove_raw_range(self, start: int, end: int) -> bool:
        raw_x = self.raw_wave_state.x
        return self._replace_raw_buffer(np.concatenate([raw_x[:start], raw_x[end:]]))

    def _insert_raw_range(self, position: int, samples: np.ndarray) -> bool:
        raw_x = self.raw_wave_state.x
        return self._replace_raw_buffer(
            np.concatenate([raw_x[:position], samples.astype(raw_x.dtype), raw_x[position:]])
        )

    def _push_undo(self, cmd: EditCommand):
        self.undo_stack.append(cmd)
        if len(self.undo_stack) > MAX_UNDO_HISTORY:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _selected_raw_range(self, no_selection_message: str) -> tuple[int, int] | None:
        """Validate the current selection and return it as raw-buffer
        sample indices, or emit a status message and return None. Checked
        in raw samples (not just seconds) so a selection shorter than one
        raw sample doesn't slip through as a nonempty range."""
        if not self.select_state.is_selected:
            self.state_changed.emit(StatusMessageState(no_selection_message))
            return None

        raw_fs = self.raw_wave_state.fs
        raw_start = int(self.select_state.sel_start * raw_fs)
        raw_end = int(self.select_state.sel_end * raw_fs)
        if raw_end <= raw_start:
            self.state_changed.emit(StatusMessageState(no_selection_message))
            return None
        return raw_start, raw_end

    def copy_selection(self) -> AudioSignal | None:
        if not self._raw_buffer_ready():
            return None
        selected = self._selected_raw_range(self.tr("No selection to copy"))
        if selected is None:
            return None

        raw_start, raw_end = selected
        raw_fs = self.raw_wave_state.fs
        return AudioSignal(self.raw_wave_state.x[raw_start:raw_end].copy(), raw_fs)

    def cut_selection(self) -> AudioSignal | None:
        if not self._raw_buffer_ready():
            return None
        selected = self._selected_raw_range(self.tr("No selection to cut"))
        if selected is None:
            return None

        raw_start, raw_end = selected
        raw_fs = self.raw_wave_state.fs
        clip = AudioSignal(self.raw_wave_state.x[raw_start:raw_end].copy(), raw_fs)

        if not self._remove_raw_range(raw_start, raw_end):
            return None
        self._push_undo(EditCommand("cut", raw_start, clip.x))
        return clip

    def paste_at(self, position_seconds: float, clip: AudioSignal):
        if not self._raw_buffer_ready():
            return

        raw_fs = self.raw_wave_state.fs
        clip_x = resample_signal(clip.x, clip.fs, raw_fs) if clip.fs != raw_fs else clip.x
        raw_position = int(np.clip(position_seconds * raw_fs, 0, len(self.raw_wave_state.x)))

        if not self._insert_raw_range(raw_position, clip_x):
            return
        self._push_undo(EditCommand("paste", raw_position, clip_x.copy()))

    def paste_at_mark(self, clip: AudioSignal):
        if not self.mark_state.is_set:
            self.state_changed.emit(
                StatusMessageState(self.tr("Set a mark (Shift+Click) before pasting"))
            )
            return
        self.paste_at(self.mark_state.position, clip)

    def _apply_command(self, cmd: EditCommand, forward: bool) -> bool:
        """Apply cmd in its original direction (forward=True, i.e. redo) or
        its inverse (forward=False, i.e. undo). A cut removes going
        forward and re-inserts in reverse; a paste is the opposite."""
        removing = (cmd.kind == "cut") == forward
        if removing:
            return self._remove_raw_range(cmd.raw_position, cmd.raw_position + len(cmd.raw_samples))
        return self._insert_raw_range(cmd.raw_position, cmd.raw_samples)

    def undo(self):
        if not self.undo_stack:
            return
        cmd = self.undo_stack.pop()
        if not self._apply_command(cmd, forward=False):
            self.undo_stack.append(cmd)  # put it back, nothing actually happened
            return
        self.redo_stack.append(cmd)

    def redo(self):
        if not self.redo_stack:
            return
        cmd = self.redo_stack.pop()
        if not self._apply_command(cmd, forward=True):
            self.redo_stack.append(cmd)  # put it back, nothing actually happened
            return
        self.undo_stack.append(cmd)

    @pyqtSlot(object)
    def on_error(self, err):
        print(err)

    def close_threads(self):
        self.audio_player.stop()
        return super().close_threads()
