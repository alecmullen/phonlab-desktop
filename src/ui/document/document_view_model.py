from dataclasses import replace

import numpy as np
import phonlab as phon
from PyQt6.QtCore import pyqtSlot

from core.edit_audio.edit_audio import EditAudio
from core.edit_audio.entity.audio_clip import AudioClip
from core.edit_audio.entity.edit_command import EditCommand, EditCommandType
from core.load_audio.entity.audio_open_options import AudioOpenOptions
from core.load_audio.entity.audio_signal import AudioSignal
from core.load_audio.load_audio import LoadAudio
from core.load_audio.prep_audio import PrepAudio
from core.parse_textgrid.parse_textgrid import ParseTextGrid, ParseTextGridError
from core.play_audio.audio_player import AudioPlayer
from core.play_audio.entity.playback_poll import PlaybackPoll
from res.constants import (
    CHANNEL_MODE_MONO,
    CHANNEL_MODE_STEREO,
    DEFAULT_WINDOW_LENGTH,
    LATENCY_WARNING_THRESHOLD_S,
    MAX_UNDO_HISTORY,
)
from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.annotation.annotation_window_state import AnnotationWindowState
from ui.base.state import State
from ui.base.view_model import ViewModel
from ui.document.state.annotation_state import AnnotationState, to_annotation_state
from ui.document.state.audio_channel_state import (
    AudioChannelState,
    to_audio_channel_state,
    to_audio_signal,
    to_audio_signals,
    to_audio_state,
)
from ui.document.state.audio_loaded import AudioLoaded
from ui.document.state.channel_state import ChannelState
from ui.document.state.document_window_state import DocumentWindowState
from ui.document.state.edit_command_state import EditCommandState
from ui.document.state.load_progress_state import LoadProgressState
from ui.document.state.mark_state import MarkState
from ui.document.state.playback_state import PlaybackState
from ui.document.state.plot_layout_state import PlotLayoutState, PlotType
from ui.document.state.select_state import SelectState
from ui.document.state.status_message_state import StatusMessageState
from ui.spectrogram.spectrogram_view_model import SpectrogramViewModel
from ui.spectrogram.state.audio_prepped import AudioPrepped
from ui.waveform.audio_wave_view_model import AudioWaveViewModel
from ui.waveform.state.audio_wave_state import to_audio_wave_state


class DocumentViewModel(ViewModel):
    def __init__(self):
        super().__init__()

        self.raw_audio_state: dict[int, AudioChannelState] = {}
        self.audio_state: dict[int, AudioChannelState] = {}
        self.channel_state: ChannelState = ChannelState()
        self.select_state: SelectState = SelectState()
        self.document_window_state: DocumentWindowState = DocumentWindowState()
        self.annotation_state: AnnotationState = AnnotationState()
        self.plot_layout_state: PlotLayoutState = PlotLayoutState()
        self.playback_state = PlaybackState()
        self.mark_state: MarkState = MarkState()
        self.audio_loaded_state: AudioLoaded = AudioLoaded()

        self.audio_options: AudioOpenOptions = AudioOpenOptions()

        self.undo_stack: list[EditCommandState] = []
        self.redo_stack: list[EditCommandState] = []

        self.audio_wave_view_model = AudioWaveViewModel()
        self.audio_wave_view_model_channel2 = AudioWaveViewModel()
        self.spectrogram_view_model = SpectrogramViewModel()
        self.annotation_view_model = AnnotationViewModel()

        self.state_changed.connect(self.on_state_changed)
        self.spectrogram_view_model.state_changed.connect(self.on_sgram_state_change)

        self.audio_player = AudioPlayer()

    @pyqtSlot(object)
    def on_state_changed(self, model: State):
        if isinstance(model, AudioLoaded):
            self.prep_audio_spectrogram()

    @pyqtSlot(object)
    def on_sgram_state_change(self, model: State):
        if isinstance(model, LoadProgressState):
            self.state_changed.emit(model)
        if isinstance(model, AudioPrepped):
            self.state_changed.emit(model)

    def toggle_wave(self):
        plots = self.plot_layout_state.plots.copy()
        if PlotType.WAVEFORM not in plots:
            plots.add(PlotType.WAVEFORM)
            self.update_audio_waveform()
        elif len(plots) > 1:
            plots.remove(PlotType.WAVEFORM)

        self.plot_layout_state = replace(self.plot_layout_state, plots=plots)
        self.state_changed.emit(self.plot_layout_state)

    def toggle_spectrogram(self):
        plots = self.plot_layout_state.plots.copy()
        if PlotType.SPECTROGRAM not in plots:
            plots.add(PlotType.SPECTROGRAM)
            self.update_spectrogram()
        elif len(plots) > 1:
            plots.remove(PlotType.SPECTROGRAM)

        self.plot_layout_state = replace(self.plot_layout_state, plots=plots)
        self.state_changed.emit(self.plot_layout_state)

    def toggle_annotations(self):
        plots = self.plot_layout_state.plots.copy()
        if PlotType.ANNOTATION not in plots:
            plots.add(PlotType.ANNOTATION)
            self.update_annotation_state()
        elif len(plots) > 1:
            plots.remove(PlotType.ANNOTATION)

        self.plot_layout_state = replace(self.plot_layout_state, plots=plots)
        self.state_changed.emit(self.plot_layout_state)

    def load_audio(self, filepath: str, options: AudioOpenOptions):
        self.audio_options = options
        self.channel_state = ChannelState(
            primary_channel=options.primary_channel, channel_mode=options.channel_mode
        )

        @pyqtSlot(object)
        def on_success(audio_signals: dict[int, AudioSignal]):
            audio = to_audio_state(audio_signals)
            primary_channel = self.set_audio(
                audio, options.primary_channel, reset_window=True
            )
            self.raw_audio_state = self.audio_state.copy()

            self.audio_loaded_state = AudioLoaded(True, primary_channel.fs)
            self.state_changed.emit(self.audio_loaded_state)

        use_case = LoadAudio(filepath)
        self.launch_use_case("load_audio", use_case, on_success, self.on_error)

    def adjust_window_if_needed(self, signal_end: int):
        window_size = self.document_window_state.end - self.document_window_state.start
        new_start = min(
            self.document_window_state.start, max(0, signal_end - window_size)
        )
        new_end = min(new_start + window_size, signal_end)
        document_window_state = replace(
            self.document_window_state,
            start=new_start,
            end=new_end,
            max_start=max(0, signal_end - window_size),
        )
        self.update_document_window(document_window_state)

    def set_audio(
        self,
        audio: dict[int, AudioChannelState],
        primary_channel_idx: int,
        reset_window: bool,
    ) -> AudioChannelState:
        self.audio_state = audio
        self.channel_state = replace(
            self.channel_state, primary_channel=primary_channel_idx
        )
        self.update_audio_waveform()

        self.remove_selection()
        self.remove_mark()

        primary_channel = self.primary_channel()
        if primary_channel is None:
            raise RuntimeError("Missing primary audio channel")

        if reset_window:
            x, fs = primary_channel.x, primary_channel.fs

            signal_end = len(x) - 1
            window_end = min(signal_end, DEFAULT_WINDOW_LENGTH * fs)

            self.document_window_state = replace(
                self.document_window_state,
                start=0,
                end=window_end,
                max_start=(signal_end - window_end),
            )
            self.update_document_window(self.document_window_state)

            shown = self.document_window_state.end - self.document_window_state.start
            msg = self.tr(
                "Duration shown {:.3f} seconds, out of {:.3f} seconds"
            ).format(shown / fs, len(x) / fs)
            self.state_changed.emit(StatusMessageState(msg))
        else:
            self.adjust_window_if_needed(len(primary_channel.x) - 1)

        return primary_channel

    def load_from_samples(self, clip: AudioClip):
        indices = sorted(clip.channels.keys())
        channel_mode = CHANNEL_MODE_STEREO if clip.is_stereo else CHANNEL_MODE_MONO
        self.audio_options = replace(
            self.audio_options, channel_mode=channel_mode, retained_channels=indices
        )
        self.channel_state = ChannelState(
            primary_channel=indices[0], channel_mode=channel_mode
        )

        audio_state = {
            idx: to_audio_channel_state(sig) for idx, sig in clip.channels.items()
        }
        primary_channel = self.set_audio(
            audio_state, primary_channel_idx=indices[0], reset_window=True
        )
        self.raw_audio_state = self.audio_state.copy()
        self.state_changed.emit(AudioLoaded(True, primary_channel.fs))

    def resample(self, target_fs: int):
        use_case = PrepAudio(
            to_audio_signals(self.raw_audio_state),
            target_fs,
            self.audio_options.retained_channels,
        )
        self.state_changed.emit(LoadProgressState(True))

        @pyqtSlot(object)
        def on_success(prepped: dict[int, AudioSignal]):
            current_primary_channel = self.primary_channel()
            if current_primary_channel is None:
                raise RuntimeError("Missing primary audio channel")

            ratio = target_fs / current_primary_channel.fs
            self.document_window_state = replace(
                self.document_window_state,
                start=int(self.document_window_state.start * ratio),
                end=int(self.document_window_state.end * ratio),
                max_start=int(self.document_window_state.max_start * ratio),
            )

            self.set_audio(
                to_audio_state(prepped), self.channel_state.primary_channel, False
            )

            self.prep_audio_spectrogram()

            self.state_changed.emit(LoadProgressState(False))

        self.launch_use_case("prep_audio", use_case, on_success, self.on_error)

    def prep_audio_spectrogram(self):
        primary_channel = self.primary_channel()
        if primary_channel is None:
            return

        stereo = self.stereo_channels()
        if stereo is not None:
            ch0, ch1 = stereo
            min_len = min(len(ch0.x), len(ch1.x))
            x = ch0.x[:min_len] + ch1.x[:min_len]
            fs = ch0.fs
        else:
            x, fs = primary_channel.x, primary_channel.fs

        self.spectrogram_view_model.prep_audio(x, fs, self.audio_options.target_fs)

    def update_spectrogram(self):
        primary_channel = self.primary_channel()
        if primary_channel is None:
            raise RuntimeError("Missing primary audio channel")

        start, end = self.document_window_state.start, self.document_window_state.end

        self.spectrogram_view_model.set_window_state(start, end, primary_channel.fs)

    def update_audio_waveform(self):
        start, end = self.document_window_state.start, self.document_window_state.end

        stereo = self.stereo_channels()
        if stereo is not None:
            # Rows are assigned by channel index, not by which channel is
            # "primary" - otherwise picking channel 1 as primary would show
            # it in both rows and channel 0 would never be displayed.
            self.audio_wave_view_model.set_wave_state(
                to_audio_wave_state(stereo[0], start, end)
            )
            self.audio_wave_view_model_channel2.set_wave_state(
                to_audio_wave_state(stereo[1], start, end)
            )
        else:
            primary_channel = self.primary_channel()
            if primary_channel is not None:
                self.audio_wave_view_model.set_wave_state(
                    to_audio_wave_state(primary_channel, start, end)
                )

    def update_annotation_state(self):
        primary_channel = self.primary_channel()
        if primary_channel is not None:
            start, end = (
                self.document_window_state.start,
                self.document_window_state.end,
            )
            fs = primary_channel.fs
            state = AnnotationWindowState(self.annotation_state, start / fs, end / fs)
            self.annotation_view_model.set_annotation_state(state)

    def play_audio(self, x: np.ndarray, fs: int, start: int):
        self.stop_audio()

        @pyqtSlot(object)
        def on_poll(playback_poll: PlaybackPoll):
            high_latency = playback_poll.latency > LATENCY_WARNING_THRESHOLD_S

            if high_latency and not self.playback_state.high_latency:
                msg = self.tr(
                    "System audio latency is a little long ({:.0f} ms). Consider using a different audio device."
                ).format(playback_poll.latency * 1000)
                self.state_changed.emit(StatusMessageState(msg))

            self.playback_state = PlaybackState(
                playback_poll.is_playing, playback_poll.current_time, high_latency
            )
            self.state_changed.emit(self.playback_state)

        self.audio_player.playback_poll.connect(on_poll)
        self.audio_player.play(x, fs, start / fs)

    def stop_audio(self):
        self.audio_player.stop()

    def update_document_window(self, document_window_state: DocumentWindowState):
        self.document_window_state = document_window_state
        self.state_changed.emit(self.document_window_state)

        if self.plot_layout_state.has_spectrogram():
            self.update_spectrogram()
        if self.plot_layout_state.has_waveform():
            self.update_audio_waveform()
        if self.plot_layout_state.has_annotation():
            self.update_annotation_state()

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
        primary_channel = self.primary_channel()
        if primary_channel is None:
            return

        start = self.document_window_state.start
        end = self.document_window_state.end
        window_size = end - start

        max_end = len(primary_channel.x) - 1

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
        primary_channel = self.primary_channel()
        if primary_channel is None:
            return

        sel_start = self.select_state.sel_start
        sel_end = self.select_state.sel_end

        if x_pos >= self.select_state.sel_anchor:
            sel_start = self.select_state.sel_anchor
            sel_end = min(x_pos, primary_channel.t[-1])

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
        primary_channel = self.primary_channel()
        if primary_channel is None:
            return
        x, fs = primary_channel.x, primary_channel.fs

        max_end = len(x) - 1
        sel_start, sel_end = self.select_state.sel_start, self.select_state.sel_end
        if sel_end > x_pos > sel_start:
            start = int(sel_start * fs)
            end = int(sel_end * fs)
            window_length = end - start
            document_window_state = replace(
                self.document_window_state,
                start=start,
                end=end,
                max_start=max_end - window_length,
            )
            self.update_document_window(document_window_state)

            self.remove_selection()

    def center_on_selection(self):
        primary_channel = self.primary_channel()
        if primary_channel is None:
            return
        if not self.select_state.is_selected:
            msg = self.tr("No selection to center on")
            self.state_changed.emit(StatusMessageState(msg))
            return

        # Calculate the center of the selection in samples
        sel_start_samples = int(self.select_state.sel_start * primary_channel.fs)
        sel_end_samples = int(self.select_state.sel_end * primary_channel.fs)
        sel_center_samples = (sel_start_samples + sel_end_samples) // 2

        # Calculate new window bounds centered on selection
        window_size = self.document_window_state.end - self.document_window_state.start
        new_start = sel_center_samples - (window_size // 2)

        self.move_start(new_start)

    def zoom_out(self, factor: float = 2):
        primary_channel = self.primary_channel()
        if primary_channel is None:
            return

        start, end = self.document_window_state.start, self.document_window_state.end

        center = start + int((end - start) / 2)
        new_size = int((end - start) * factor)

        max_end = len(primary_channel.x) - 1

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
        primary_channel = self.primary_channel()
        if primary_channel is None:
            return

        start, end = self.document_window_state.start, self.document_window_state.end

        center = start + int((end - start) / 2)
        new_size = int((end - start) / factor)
        new_size = max(new_size, 50)

        new_end = center + int(new_size / 2)
        new_start = new_end - new_size

        max_end = len(primary_channel.x) - 1

        window_length = new_end - new_start

        self.document_window_state = replace(
            self.document_window_state,
            start=new_start,
            end=new_end,
            max_start=(max_end - window_length),
        )
        self.update_document_window(self.document_window_state)

    def show_all(self):
        primary_channel = self.primary_channel()
        if primary_channel is None:
            return

        end = len(primary_channel.x) - 1

        self.document_window_state = DocumentWindowState(start=0, end=end)
        self.update_document_window(self.document_window_state)

    def _playback_section(self, start: int, end: int) -> tuple[np.ndarray, int] | None:
        """The samples to play for [start:end), as stereo (N, 2) if both
        channels are active, else mono (N,). Channel-index order (not
        primary-first) is correct here regardless of which channel is
        "primary" - it's just left/right output order."""
        stereo = self.stereo_channels()
        if stereo is not None:
            ch0, ch1 = stereo
            min_len = min(len(ch0.x), len(ch1.x))
            end = min(end, min_len)
            if start >= end:
                return None
            section = np.stack([ch0.x[start:end], ch1.x[start:end]], axis=1)
            return section, ch0.fs

        channel = self.primary_channel()
        if channel is None:
            return None
        if start >= end:
            return None
        return channel.x[start:end], channel.fs

    def play_selected_audio(self):
        channel = self.primary_channel()
        if channel is None:
            self.state_changed.emit(
                StatusMessageState(self.tr("Audio is still loading, please wait."))
            )
            return

        start = int(self.select_state.sel_start * channel.fs)
        end = int(self.select_state.sel_end * channel.fs)

        section = self._playback_section(start, end)
        if section is not None:
            self.play_audio(section[0], section[1], start=start)

    def play_visible_audio(self):
        start, end = self.document_window_state.start, self.document_window_state.end

        if self.primary_channel() is None:
            self.state_changed.emit(
                StatusMessageState(self.tr("Audio is still loading, please wait."))
            )
            return

        section = self._playback_section(start, end)
        if section is not None:
            self.play_audio(section[0], section[1], start=start)

    def primary_channel(self) -> AudioChannelState | None:
        if self.channel_state.primary_channel in self.audio_state:
            return self.audio_state[self.channel_state.primary_channel]
        else:
            return None

    def stereo_channels(self) -> tuple[AudioChannelState, AudioChannelState] | None:
        """Both channels of a stereo document, in channel-index order (not
        primary-first) so which channel is "primary" doesn't affect which
        waveform row or playback output channel each one is. None outside
        stereo mode, or if either channel hasn't loaded yet."""
        if self.channel_state.channel_mode != CHANNEL_MODE_STEREO:
            return None
        indices = sorted(self.audio_options.retained_channels)
        if len(indices) != 2 or not all(idx in self.audio_state for idx in indices):
            return None
        return (self.audio_state[indices[0]], self.audio_state[indices[1]])

    def set_mark(self, x_pos: float):
        self.mark_state = MarkState(position=x_pos, is_set=True)
        self.state_changed.emit(self.mark_state)

    def remove_mark(self):
        self.mark_state = MarkState()
        self.state_changed.emit(self.mark_state)

    def mark_position_or_warn(self) -> float | None:
        """The current mark position, or None (with a status message) if no
        mark is set. Callers that may need to promote this document to
        stereo before pasting must capture this BEFORE that happens, since
        set_audio() clears the mark as a side effect."""
        if not self.mark_state.is_set:
            self.state_changed.emit(
                StatusMessageState(self.tr("Set a mark (Shift+Click) before pasting"))
            )
            return None
        return self.mark_state.position

    def _audio_ready(self) -> bool:
        if not self.audio_state:
            self.state_changed.emit(
                StatusMessageState(self.tr("Audio is still loading, please wait."))
            )
            return False
        return True

    def _replace_channels(self, new_signals: dict[int, AudioSignal]) -> bool:
        """Commit new sample data for one or more channels as a single,
        atomic edit - always one set_audio() call for the whole dict, never
        one per channel, since set_audio() also drives selection/mark/window
        updates and a spectrogram refresh that should only fire once per
        logical edit."""
        if any(len(sig.x) == 0 for sig in new_signals.values()):
            self.state_changed.emit(
                StatusMessageState(self.tr("Cannot remove entire selection"))
            )
            return False

        audio_state = self.audio_state
        for idx, sig in new_signals.items():
            audio_state[idx] = to_audio_channel_state(sig)
        self.set_audio(
            audio_state, self.channel_state.primary_channel, reset_window=False
        )
        self.prep_audio_spectrogram()
        return True

    def _push_undo(self, cmd: EditCommandState):
        self.undo_stack.append(cmd)
        if len(self.undo_stack) > MAX_UNDO_HISTORY:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _stereo_edit_channels(self) -> tuple[AudioChannelState, AudioChannelState]:
        """Both stereo channels, guaranteed equal length - the invariant every
        stereo edit relies on to apply one resolved range/index to both
        channels without re-deriving it per channel."""
        stereo = self.stereo_channels()
        if stereo is None:
            raise RuntimeError("Missing stereo audio channels")
        ch0, ch1 = stereo
        if len(ch0.x) != len(ch1.x):
            raise RuntimeError("Stereo channels have desynced lengths")
        return ch0, ch1

    def copy_selection(self) -> AudioClip | None:
        if not self._audio_ready():
            return None

        if not self.select_state.is_selected:
            self.state_changed.emit(StatusMessageState(self.tr("No selection to copy")))
            return None

        cmd = EditCommand(
            EditCommandType.COPY, self.select_state.sel_start, self.select_state.sel_end
        )

        stereo = self.stereo_channels()
        if stereo is None:
            primary_channel = self.primary_channel()
            if primary_channel is None:
                raise RuntimeError("Missing primary audio channel")

            result = EditAudio(to_audio_signal(primary_channel), cmd).invoke()
            if result is None:
                self.state_changed.emit(
                    StatusMessageState(self.tr("No selection to copy"))
                )
                return None
            return AudioClip({self.channel_state.primary_channel: result.new_clip})

        ch0, ch1 = self._stereo_edit_channels()
        result0 = EditAudio(to_audio_signal(ch0), cmd).invoke()
        if result0 is None:
            self.state_changed.emit(StatusMessageState(self.tr("No selection to copy")))
            return None

        start, length = result0.start_idx, len(result0.new_clip.x)
        clip1 = AudioSignal(ch1.x[start : start + length], ch1.fs)
        return AudioClip({0: result0.new_clip, 1: clip1})

    def cut_selection(self) -> AudioClip | None:
        if not self._audio_ready():
            return None

        if not self.select_state.is_selected:
            self.state_changed.emit(StatusMessageState(self.tr("No selection to cut")))
            return None

        cmd = EditCommand(
            EditCommandType.CUT, self.select_state.sel_start, self.select_state.sel_end
        )

        stereo = self.stereo_channels()
        if stereo is None:
            primary_channel = self.primary_channel()
            if primary_channel is None:
                raise RuntimeError("Missing primary audio channel")

            result = EditAudio(to_audio_signal(primary_channel), cmd).invoke()
            if result is None:
                self.state_changed.emit(
                    StatusMessageState(self.tr("No selection to cut"))
                )
                return None

            idx = self.channel_state.primary_channel
            self._replace_channels({idx: result.new_channel})
            self._push_undo(
                EditCommandState(
                    EditCommandType.CUT, result.start_idx, {idx: result.new_clip.x}
                )
            )
            return AudioClip({idx: result.new_clip})

        ch0, ch1 = self._stereo_edit_channels()
        result0 = EditAudio(to_audio_signal(ch0), cmd).invoke()
        if result0 is None:
            self.state_changed.emit(StatusMessageState(self.tr("No selection to cut")))
            return None

        start, length = result0.start_idx, len(result0.new_clip.x)
        new_x1 = np.concatenate([ch1.x[:start], ch1.x[start + length :]])
        clip1_x = ch1.x[start : start + length]

        self._replace_channels({0: result0.new_channel, 1: AudioSignal(new_x1, ch1.fs)})
        self._push_undo(
            EditCommandState(
                EditCommandType.CUT, start, {0: result0.new_clip.x, 1: clip1_x}
            )
        )
        return AudioClip({0: result0.new_clip, 1: AudioSignal(clip1_x, ch1.fs)})

    def paste_at(self, start_time: float, clip: AudioClip) -> AudioClip | None:
        """Paste `clip`, which must already match this document's channel
        count - a mono/stereo mismatch has to be resolved first via
        reconcile_clip_for_paste() (a dialog-driven choice made by the
        View), not here."""
        if not self._audio_ready():
            return None

        stereo = self.stereo_channels()
        if stereo is None:
            if clip.is_stereo:
                raise RuntimeError("Stereo clip pasted without reconciliation")

            idx = self.channel_state.primary_channel
            channel = self.primary_channel()
            if channel is None:
                raise RuntimeError("Missing primary audio channel")
            mono_clip = (
                clip.channels[idx]
                if idx in clip.channels
                else next(iter(clip.channels.values()))
            )

            result = EditAudio(
                to_audio_signal(channel),
                EditCommand(
                    EditCommandType.PASTE,
                    start_time,
                    clip_x=mono_clip.x,
                    clip_fs=mono_clip.fs,
                ),
            ).invoke()
            if result is None:
                raise RuntimeError("Paste failed unexpectedly")

            self._replace_channels({idx: result.new_channel})
            self._push_undo(
                EditCommandState(
                    EditCommandType.PASTE, result.start_idx, {idx: result.new_clip.x}
                )
            )
            return AudioClip({idx: result.new_clip})

        if not clip.is_stereo:
            raise RuntimeError("Mono clip pasted without reconciliation")

        ch0, ch1 = self._stereo_edit_channels()
        clip0, clip1 = clip.channels[0], clip.channels[1]

        result0 = EditAudio(
            to_audio_signal(ch0),
            EditCommand(
                EditCommandType.PASTE, start_time, clip_x=clip0.x, clip_fs=clip0.fs
            ),
        ).invoke()
        if result0 is None:
            raise RuntimeError("Paste failed unexpectedly")

        result1 = EditAudio(
            to_audio_signal(ch1),
            EditCommand(
                EditCommandType.PASTE,
                start_time,
                clip_x=clip1.x,
                clip_fs=clip1.fs,
                snapped_start_idx=result0.start_idx,
            ),
        ).invoke()
        if result1 is None:
            raise RuntimeError("Paste failed unexpectedly")

        self._replace_channels({0: result0.new_channel, 1: result1.new_channel})
        self._push_undo(
            EditCommandState(
                EditCommandType.PASTE,
                result0.start_idx,
                {0: result0.new_clip.x, 1: result1.new_clip.x},
            )
        )
        return AudioClip({0: result0.new_clip, 1: result1.new_clip})

    def paste_at_mark(self, clip: AudioClip):
        position = self.mark_position_or_warn()
        if position is None:
            return
        self.paste_at(position, clip)

    def _tiny_noise(self, length: int, fs: int, dtype: np.dtype) -> AudioSignal:
        """A quiet noise-filled channel for the "empty" side of a synthesized
        stereo pair - either the non-chosen channel of a mono clip pasted
        into a stereo document, or a brand-new channel created when
        promoting a mono document to stereo. phon.prep_audio's
        add_tiny_noise adds tiny noise to every sample (not just exact
        zeros, despite its docstring) - harmless here since the input is
        always all-zero."""
        zeros = np.zeros(length, dtype=np.float32)
        x, _ = phon.prep_audio(
            zeros, fs, target_fs=fs, scale=False, add_tiny_noise=True
        )
        return AudioSignal(x.astype(dtype), fs)

    def reconcile_clip_for_paste(
        self, clip: AudioClip, channel_choice: int
    ) -> AudioClip:
        """Resolve a mono/stereo mismatch between `clip` and this document
        ahead of a paste, given the user's channel_choice (0=left, 1=right)
        for where the real audio should go. NOT a pure function: for a
        stereo clip pasted into a mono document, this promotes the document
        to stereo as a side effect (audio_state, raw_audio_state,
        channel_state, audio_options) and returns `clip` unchanged; for a
        mono clip pasted into a stereo document, it returns a synthesized
        stereo clip instead, with no side effects."""
        stereo = self.stereo_channels()
        other = 1 - channel_choice

        if stereo is not None:
            mono_signal = next(iter(clip.channels.values()))
            noise = self._tiny_noise(
                len(mono_signal.x), mono_signal.fs, mono_signal.x.dtype
            )
            return AudioClip({channel_choice: mono_signal, other: noise})

        old_idx = self.channel_state.primary_channel
        existing = self.audio_state.get(old_idx)
        raw_existing = self.raw_audio_state.get(old_idx)
        if existing is None or raw_existing is None:
            raise RuntimeError("Missing primary audio channel")

        prepped_noise = self._tiny_noise(len(existing.x), existing.fs, existing.x.dtype)
        raw_noise = self._tiny_noise(
            len(raw_existing.x), raw_existing.fs, raw_existing.x.dtype
        )

        audio_state = {
            channel_choice: existing,
            other: to_audio_channel_state(prepped_noise),
        }
        self.raw_audio_state = {
            channel_choice: raw_existing,
            other: to_audio_channel_state(raw_noise),
        }

        self.audio_options = replace(
            self.audio_options,
            channel_mode=CHANNEL_MODE_STEREO,
            retained_channels=[0, 1],
        )
        self.channel_state = replace(
            self.channel_state,
            channel_mode=CHANNEL_MODE_STEREO,
            primary_channel=channel_choice,
        )
        self.set_audio(audio_state, channel_choice, reset_window=False)

        # set_audio() doesn't re-derive plot layout - only AudioLoaded/
        # PlotLayoutState events do - so re-emit it to rebuild the view with
        # a second waveform row now that this document is genuinely stereo.
        self.state_changed.emit(self.plot_layout_state)

        return clip

    def _apply_command(self, cmd: EditCommandState, forward: bool) -> bool:
        """Apply cmd in its original direction (forward=True, i.e. redo) or
        its inverse (forward=False, i.e. undo). A cut removes going
        forward and re-inserts in reverse; a paste is the opposite. Applies
        the same start_idx to every channel cmd touched (1 for mono, 2 for
        stereo), keeping them in sync."""
        removing = (cmd.type == "cut") == forward
        new_signals = {}
        for idx, clip_x in cmd.clips.items():
            channel = self.audio_state.get(idx)
            if channel is None:
                raise RuntimeError(f"Missing channel {idx} for undo/redo")

            if removing:
                new_x = np.concatenate(
                    [
                        channel.x[: cmd.start_idx],
                        channel.x[cmd.start_idx + len(clip_x) :],
                    ]
                )
            else:
                new_x = np.concatenate(
                    [channel.x[: cmd.start_idx], clip_x, channel.x[cmd.start_idx :]]
                )
            new_signals[idx] = AudioSignal(new_x, channel.fs)

        return self._replace_channels(new_signals)

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

    def parse_textgrid(self, path: str):
        use_case = ParseTextGrid(path)
        try:
            self.annotation_state = to_annotation_state(use_case.invoke())
            self.update_annotation_state()
        except ParseTextGridError as e:
            self.state_changed.emit(StatusMessageState(str(e)))

    @pyqtSlot(object)
    def on_error(self, err: Exception):
        print(err)

    def close_threads(self) -> None:
        self.audio_player.stop()
        return super().close_threads()
