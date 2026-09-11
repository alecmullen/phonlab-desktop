from dataclasses import replace

import numpy as np
import phonlab as phon
from PyQt6.QtCore import pyqtSignal, pyqtSlot

from core.load_audio.entity.audio_signal import AudioSignal
from core.load_audio.prep_audio import PrepAudio
from core.spectrogram.compute_sgram import ComputeSpectrogram
from core.spectrogram.compute_sgram_mmap import ComputeSpectrogramMmap
from core.spectrogram.entity.spectrogram import Spectrogram
from core.spectrogram.entity.spectrogram_mmap import SpectrogramMmap
from res.constants import MAX_SGRAM_LENGTH
from ui.base.view_model import ViewModel
from ui.document.state.audio_channel_state import (
    AudioChannelState,
    to_audio_state,
)
from ui.document.state.load_progress_state import LoadProgressState
from ui.spectrogram.state.spectrogram_state import SpectrogramState
from ui.spectrogram.state.spectrogram_window_state import SpectrogramWindowState


class SpectrogramViewModel(ViewModel):
    audio_prepped = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.prepped_audio_state: AudioChannelState | None = None
        self.sgram_state: SpectrogramState = SpectrogramState()
        self.window_state: SpectrogramWindowState = SpectrogramWindowState()

        self._buffer_generation = 0

        self.audio_prepped.connect(self.compute_spectrogram)

    @pyqtSlot(object, object)
    def prep_audio(self, x: np.ndarray, fs: int, target_fs: int | None = None):
        if target_fs is None:
            if self.prepped_audio_state is None:
                raise RuntimeError(
                    "Cannot prep audio for the first time without a target sample rate"
                )
            target_fs = self.prepped_audio_state.fs
        use_case = PrepAudio({0: AudioSignal(x, fs)}, target_fs, [0])
        self.state_changed.emit(LoadProgressState(True))

        @pyqtSlot(object)
        def on_success(prepped: dict[int, AudioSignal]):
            self.prepped_audio_state = to_audio_state(prepped)[0]
            self.invalidate_spectrogram()
            self.state_changed.emit(LoadProgressState(False))
            self.audio_prepped.emit()

        self.launch_use_case("prep_audio", use_case, on_success, self.on_error)

    @pyqtSlot()
    def compute_spectrogram(self):
        if self.prepped_audio_state is None:
            return

        x, t, fs = (
            self.prepped_audio_state.x,
            self.prepped_audio_state.t,
            self.prepped_audio_state.fs,
        )
        start, end = self.window_state.start, self.window_state.end

        if (end - start) / fs > MAX_SGRAM_LENGTH:
            self.sgram_state = replace(self.sgram_state, is_showing=False)
            self.state_changed.emit(self.sgram_state)
            return

        self.load_spectrogram_window(x, t, fs, start, end)
        self.load_spectrogram_mmap(x, fs)

    def load_spectrogram_window(
        self, x: np.ndarray, t: np.ndarray, fs: int, start: int, end: int
    ):
        if (
            self.sgram_state.sxx_mmap is not None
            and self.sgram_state.t_mmap is not None
            and self.sgram_state.samples_computed > end
        ):
            frames_computed = self.sgram_state.frames_computed
            sfr = np.abs(self.sgram_state.t_mmap[:frames_computed] - t[start]).argmin()
            efr = np.abs(self.sgram_state.t_mmap[:frames_computed] - t[end]).argmin()

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
            t, f, sxx = phon.compute_sgram(x[start:end], fs, 0.008, 0.003, 8)

            self.sgram_state = replace(
                self.sgram_state,
                t_window=t + (start / fs),
                sxx_window=sxx,
                f=f,
                is_showing=True,
            )
            self.update_sxx_extrema(sxx)
            self.state_changed.emit(self.sgram_state)

            generation = self._buffer_generation

            @pyqtSlot(object)
            def on_success(sgram: Spectrogram):
                if generation != self._buffer_generation:
                    return
                self.sgram_state = replace(
                    self.sgram_state,
                    t_window=sgram.t + (start / fs),
                    sxx_window=sgram.sxx,
                    f=sgram.f,
                    is_showing=True,
                )
                self.update_sxx_extrema(sgram.sxx)
                self.state_changed.emit(self.sgram_state)

            use_case = ComputeSpectrogram(x[start:end], fs)
            self.launch_use_case("sgram_window", use_case, on_success, self.on_error)

    def load_spectrogram_mmap(self, x: np.ndarray, fs: int):
        if self.sgram_state.sxx_mmap is None or self.sgram_state.t_mmap is None:
            self.state_changed.emit(LoadProgressState(True))

            generation = self._buffer_generation

            @pyqtSlot(object)
            def on_success(sgram: SpectrogramMmap):
                if generation != self._buffer_generation:
                    return
                self.sgram_state = replace(
                    self.sgram_state,
                    sxx_mmap=sgram.sxx_mmap,
                    t_mmap=sgram.t_mmap,
                    frames_per_sec=sgram.frames_per_sec,
                    frames_computed=sgram.frames_computed,
                    samples_computed=sgram.samples_computed,
                )
                self.update_sxx_extrema(sgram.sxx_mmap)
                self.state_changed.emit(LoadProgressState(False))

            use_case = ComputeSpectrogramMmap(x, fs)
            self.launch_use_case(
                "sgram_mmap", use_case, on_success, self.on_error, only_once=True
            )

    def adjust_gray_scale(self, adjustment: float):
        gray_cutoff = self.sgram_state.gray_cutoff + adjustment
        gray_cutoff = max(0.0, min(0.7, gray_cutoff))
        self.sgram_state = replace(self.sgram_state, gray_cutoff=gray_cutoff)
        self.state_changed.emit(self.sgram_state)

    def update_sxx_extrema(self, sxx: np.ndarray | np.memmap):
        self.sgram_state = replace(
            self.sgram_state,
            min_sxx=min(self.sgram_state.min_sxx, np.min(sxx)),
            max_sxx=max(self.sgram_state.max_sxx, np.max(sxx)),
        )

    def invalidate_spectrogram(self):
        self._buffer_generation += 1
        self.close_thread("sgram_mmap")
        self.close_thread("sgram_window")
        self.sgram_state = replace(
            self.sgram_state, sxx_mmap=None, t_mmap=None, frames_computed=0
        )

    def set_window_state(
        self, start: int, end: int, raw_fs: int, target_fs: int | None = None
    ):
        if target_fs is None:
            if self.prepped_audio_state is None:
                raise RuntimeError(
                    "Cannot set spectrogram window without a target sample rate"
                )
            target_fs = self.prepped_audio_state.fs

        # convert to prepped audio sample indices
        fs_ratio = target_fs / raw_fs
        start_idx = int(start * fs_ratio)
        end_idx = int(end * fs_ratio)

        self.window_state = SpectrogramWindowState(start_idx, end_idx)
        self.compute_spectrogram()

    @pyqtSlot(object)
    def on_error(self, err: Exception):
        print(err)
