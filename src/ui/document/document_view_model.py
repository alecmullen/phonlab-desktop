from dataclasses import replace

import numpy as np
import phonlab as phon
from PyQt6.QtCore import QTimer, pyqtSlot

from core.edit_audio.edit_audio import EditAudio
from core.edit_audio.entity.edit_command import EditCommand
from core.load_audio.entity.audio_open_options import AudioOpenOptions
from core.load_audio.entity.audio_signal import AudioSignal
from core.load_audio.load_audio import LoadAudio
from core.load_audio.prep_audio import PrepAudio
from core.play_audio.audio_player import AudioPlayer
from core.play_audio.entity.playback_poll import PlaybackPoll
from core.spectrogram.compute_sgram import ComputeSpectrogram
from core.spectrogram.compute_sgram_mmap import ComputeSpectrogramMmap
from core.spectrogram.entity.spectrogram import Spectrogram
from core.spectrogram.entity.spectrogram_mmap import SpectrogramMmap
from res.constants import MAX_SGRAM_LENGTH, MAX_UNDO_HISTORY
from ui.base.view_model import ViewModel
from ui.document.state.audio_channel_state import (
    AudioChannelState,
    to_audio_channel_state,
    to_audio_signal,
)
from ui.document.state.channel_state import ChannelState
from ui.document.state.document_window_state import DocumentWindowState
from ui.document.state.edit_command_state import EditCommandState
from ui.document.state.load_progress_state import LoadProgressState
from ui.document.state.mark_state import MarkState
from ui.document.state.playback_state import PlaybackState
from ui.document.state.plot_layout_state import PlotLayoutState
from ui.document.state.select_state import SelectState
from ui.document.state.sgram_state import SpectrogramState
from ui.document.state.status_message_state import StatusMessageState
from ui.document.state.waveform_state import WaveformState, to_waveform_state

LATENCY_WARNING_THRESHOLD_S = 0.1  # audacity's own reference for "robust" latency


class DocumentViewModel(ViewModel):
    def __init__(self):
        super().__init__()
        self.raw_audio_state: list[AudioChannelState] = None
        self.prepped_audio_state: dict[AudioChannelState] = {}
        self.waveform_state: WaveformState = WaveformState()
        self.channel_state: ChannelState = ChannelState()
        self.sgram_state: SpectrogramState = SpectrogramState()
        self.select_state: SelectState = SelectState()
        self.document_window_state: DocumentWindowState = DocumentWindowState()
        self.plot_layout_state: PlotLayoutState = PlotLayoutState()
        self.playback_state = PlaybackState()
        self.mark_state: MarkState = MarkState()

        self.undo_stack: list[EditCommandState] = []
        self.redo_stack: list[EditCommandState] = []
        self._buffer_generation = 0

        self.click_timer: QTimer | None = None

        self.audio_player = AudioPlayer()

    def load_audio(self, filepath: str, options: AudioOpenOptions):
        self.channel_state = ChannelState(primary_channel=options.primary_channel, channel_mode=options.channel_mode)

        @pyqtSlot(object)
        def on_success(audio_signals: list[AudioSignal]):
            raw_audio = [to_audio_channel_state(sig) for sig in audio_signals]
            self.set_raw_audio(raw_audio, options.primary_channel, reset_window=True)

            self.prep_audio(audio_signals, options)

        use_case = LoadAudio(filepath)
        self.launch_use_case("load_audio", use_case, on_success, self.on_error)

    def prep_audio(self, channels: list[AudioSignal], options: AudioOpenOptions):
        use_case = PrepAudio(channels, options.target_fs, options.retained_channels)

        @pyqtSlot(object)
        def on_success(prepped: dict[int, AudioSignal]):
            self.prepped_audio_state = { idx: to_audio_channel_state(sig) for idx, sig in prepped.items() }

        self.launch_use_case("prep_audio", use_case, on_success, self.on_error)

    def prep_edited_audio_channel(self, new_raw_signal: AudioSignal, target_fs, channel_idx: int):
        use_case = PrepAudio([new_raw_signal], target_fs, [0])

        @pyqtSlot(object)
        def on_success(prepped: dict[int, AudioSignal]):
            # Merge existing channel dictionary with the newly prepped channel.
            # We passed a single channel to PrepAudio, so we retreieve it at prepped[0]
            new_prepped_signal = prepped[0]
            self.prepped_audio_state = self.prepped_audio_state | {channel_idx: new_prepped_signal}

        self.launch_use_case("prep_audio", use_case, on_success, self.on_error)

    def adjust_window_if_needed(self, signal_end: int):
        window_size = self.document_window_state.end - self.document_window_state.start
        new_start = min(self.document_window_state.start, max(0, signal_end - window_size))
        new_end = min(new_start + window_size, signal_end)
        self.document_window_state = replace(
            self.document_window_state,
            start=new_start,
            end=new_end,
            max_start=max(0, signal_end - window_size),
        )

    def set_raw_audio(self, raw_audio: list[AudioChannelState], primary_channel: int, reset_window: bool):
        self.raw_audio_state = raw_audio
        self.waveform_state = to_waveform_state(raw_audio[primary_channel])
        self.state_changed.emit(self.waveform_state)

        self._invalidate_spectrogram()
        self.remove_selection()
        self.remove_mark()

        if reset_window:
            primary_channel = self.get_primary_raw_channel()
            x, fs = primary_channel.x, primary_channel.fs

            signal_end = len(x) - 1
            window_end = min(signal_end, MAX_SGRAM_LENGTH * fs)

            self.document_window_state = replace(
                self.document_window_state,
                start=0,
                end=window_end,
                max_start=(signal_end - window_end),
            )

            self.state_changed.emit(self.document_window_state)

            shown = (
                self.document_window_state.end - self.document_window_state.start
            )
            msg = self.tr(
                "Duration shown {:.3f} seconds, out of {:.3f} seconds"
            ).format(shown / fs, len(x) / fs)
            self.state_changed.emit(StatusMessageState(msg))
        else:
            self.adjust_window_if_needed(len(self.waveform_state.x) - 1)

    def load_from_samples(self, x: np.ndarray, fs: int, target_fs: int):
        raw_audio_state = [AudioChannelState(x, fs)]
        self.set_raw_audio(raw_audio_state, primary_channel=0, reset_window=True)

        self.prep_audio([AudioSignal(x, fs)], AudioOpenOptions(target_fs=target_fs, channel_mode="mono", retained_channels=[0], primary_channel=0))

    def show_spectrogram(self, show: bool):
        self.plot_layout_state = replace(self.plot_layout_state, is_spectrogram=show)
        self.state_changed.emit(self.plot_layout_state)
        if show:
            self.compute_spectrogram()

    def compute_spectrogram(self):
        if not self.plot_layout_state.is_spectrogram:
            return

        prepped_audio_signal = self.get_primary_prepped_channel()
        x, fs = prepped_audio_signal.x, prepped_audio_signal.fs

        start, end = self.document_window_state.start, self.document_window_state.end

        #convert to prepped audio sample indices
        start_t = start / self.waveform_state.fs
        end_t = end / self.waveform_state.fs
        start_idx = int(start_t * fs)
        end_idx = int(end_t * fs)

        if (end_idx - start_idx) / fs > MAX_SGRAM_LENGTH:
            self.sgram_state = replace(self.sgram_state, is_showing=False)
            self.state_changed.emit(self.sgram_state)
            return

        self.load_spectrogram_window(x, fs, start_idx, end_idx, start_t, end_t)
        self.load_spectrogram_mmap(x, fs)

    def load_spectrogram_window(self, x: np.ndarray, fs: int, start_idx: int, end_idx: int, start_t: float, end_t: float):
        if (
            self.sgram_state.sxx_mmap is not None
            and self.sgram_state.t_mmap is not None
            and self.sgram_state.samples_computed > end_idx
        ):
            frames_computed = self.sgram_state.frames_computed
            sfr = np.abs(
                self.sgram_state.t_mmap[:frames_computed] - start_t
            ).argmin()
            efr = np.abs(
                self.sgram_state.t_mmap[:frames_computed] - end_t
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
            t, f, sxx = phon.compute_sgram(x[start_idx:end_idx], fs, 0.008, 0.003, 9)

            self.sgram_state = replace(
                self.sgram_state,
                t_window=t + start_t,
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
                    t_window=sgram.t + start_t,
                    sxx_window=sgram.sxx,
                    f=sgram.f,
                    is_showing=True,
                )
                self.state_changed.emit(self.sgram_state)

            use_case = ComputeSpectrogram(x[start_idx:end_idx], fs)
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

    def _invalidate_spectrogram(self):
        self._buffer_generation += 1
        self.close_thread("sgram_mmap")
        self.close_thread("sgram_window")

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
        self.audio_player.play(x, fs, start / fs)

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
        max_end = len(self.waveform_state.x) - 1

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
            sel_end = min(x_pos, self.waveform_state.t[-1])
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
        x, fs = self.waveform_state.x, self.waveform_state.fs
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
        sel_start_samples = int(self.select_state.sel_start * self.waveform_state.fs)
        sel_end_samples = int(self.select_state.sel_end * self.waveform_state.fs)
        sel_center_samples = (sel_start_samples + sel_end_samples) // 2

        # Calculate new window bounds centered on selection
        window_size = self.document_window_state.end - self.document_window_state.start
        new_start = sel_center_samples - (window_size // 2)

        self.move_start(new_start)

    def zoom_out(self, factor: float = 2):
        start, end = self.document_window_state.start, self.document_window_state.end

        center = start + int((end - start) / 2)
        new_size = int((end - start) * factor)
        max_end = len(self.waveform_state.x) - 1

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

        max_end = len(self.waveform_state.x) - 1
        window_length = new_end - new_start

        self.document_window_state = replace(
            self.document_window_state, start=new_start, end=new_end, max_start=(max_end - window_length)
        )
        self.state_changed.emit(self.document_window_state)

    def show_all(self):
        end = len(self.waveform_state.x) - 1
        self.document_window_state = DocumentWindowState(start=0, end=end)
        self.state_changed.emit(self.document_window_state)

    def play_selected_audio(self):
        fs = self.waveform_state.fs
        start = int(self.select_state.sel_start * fs)
        end = int(self.select_state.sel_end * fs)

        if start != end:
            section = self.waveform_state.x[start:end]
            self.play_audio(section, fs, start=start)

    def play_visible_audio(self):
        start, end = self.document_window_state.start, self.document_window_state.end

        if len(self.waveform_state.x) > 0:
            section = self.waveform_state.x[start:end]
            self.play_audio(section, self.waveform_state.fs, start=start)

    def get_primary_raw_channel(self) -> AudioChannelState:
        return self.raw_audio_state[self.channel_state.primary_channel]

    def get_primary_prepped_channel(self) -> AudioChannelState:
        return self.prepped_audio_state[self.channel_state.primary_channel]

    def set_mark(self, x_pos: float):
        self.mark_state = MarkState(position=x_pos, is_set=True)
        self.state_changed.emit(self.mark_state)

    def remove_mark(self):
        self.mark_state = MarkState()
        self.state_changed.emit(self.mark_state)

    def _raw_audio_ready(self) -> bool:
        if self.raw_audio_state is None:
            self.state_changed.emit(
                StatusMessageState(self.tr("Audio is still loading, please wait."))
            )
            return False
        return True

    def _replace_primary_channel(self, new_raw_signal: AudioSignal) -> bool:
        if len(new_raw_signal.x) == 0:
            self.state_changed.emit(
                StatusMessageState(self.tr("Cannot remove entire selection"))
            )
            return False

        raw_audio_state =  self.raw_audio_state
        raw_audio_state[self.channel_state.primary_channel] = to_audio_channel_state(new_raw_signal)
        self.set_raw_audio(raw_audio_state, self.channel_state.primary_channel, reset_window=False)

        channel_idx = self.channel_state.primary_channel
        old_signal = self.prepped_audio_state[channel_idx]
        self.prep_edited_audio_channel(new_raw_signal, old_signal.fs, channel_idx)
        return True

    def _push_undo(self, cmd: EditCommandState):
        self.undo_stack.append(cmd)
        if len(self.undo_stack) > MAX_UNDO_HISTORY:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def copy_selection(self) -> AudioSignal | None:
        if not self._raw_audio_ready():
            return None
        if not self.select_state.is_selected:
            self.state_changed.emit(StatusMessageState(self.tr("No selection to copy")))
            return None

        result = EditAudio(
            to_audio_signal(self.get_primary_raw_channel()),
            EditCommand("copy", self.select_state.sel_start, self.select_state.sel_end)
        ).invoke()

        if result is None:
            self.state_changed.emit(StatusMessageState(self.tr("No selection to copy")))
            return None
        else:
            return result.new_clip

    def cut_selection(self) -> AudioSignal | None:
        if not self._raw_audio_ready():
            return None
        if not self.select_state.is_selected:
            self.state_changed.emit(StatusMessageState(self.tr("No selection to cut")))
            return None

        result = EditAudio(
            to_audio_signal(self.get_primary_raw_channel()),
            EditCommand("cut", self.select_state.sel_start, self.select_state.sel_end)
        ).invoke()

        if result is None:
            self.state_changed.emit(StatusMessageState(self.tr("No selection to cut")))
            return None
        else:
            self._replace_primary_channel(result.new_channel)
            self._push_undo(EditCommandState("cut", result.start_idx, result.new_clip.x))
            return result.new_clip

    def paste_at(self, start_time: float, clip: AudioSignal):
        if not self._raw_audio_ready():
            return

        result = EditAudio(
            to_audio_signal(self.get_primary_raw_channel()),
            EditCommand("paste", start_time, clip_x=clip.x, clip_fs=clip.fs)
        ).invoke()

        if result is None:
            return None
        else:
            self._replace_primary_channel(result.new_channel)
            self._push_undo(EditCommandState("paste", result.start_idx, result.new_clip))
            return result.new_clip

    def paste_at_mark(self, clip: AudioSignal):
        if not self.mark_state.is_set:
            self.state_changed.emit(
                StatusMessageState(self.tr("Set a mark (Shift+Click) before pasting"))
            )
            return
        self.paste_at(self.mark_state.position, clip)

    def _apply_command(self, cmd: EditCommandState, forward: bool) -> bool:
        """Apply cmd in its original direction (forward=True, i.e. redo) or
        its inverse (forward=False, i.e. undo). A cut removes going
        forward and re-inserts in reverse; a paste is the opposite."""
        channel = self.get_primary_raw_channel()

        removing = (cmd.type == "cut") == forward
        if removing:
            new_x = np.concatenate([channel.x[:cmd.start_idx], channel.x[cmd.start_idx + len(cmd.clip_x):]])
            return self._replace_primary_channel(AudioSignal(new_x, channel.fs))
        
        new_x = np.concatenate([channel.x[:cmd.start_idx], cmd.clip_x, channel.x[cmd.start_idx:]])
        return self._replace_primary_channel(AudioSignal(new_x, channel.fs))

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
