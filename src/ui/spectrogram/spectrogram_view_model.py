from dataclasses import replace

import numpy as np
import phonlab as phon
from PyQt6.QtCore import pyqtSlot

from core.spectrogram.compute_sgram import ComputeSpectrogram
from core.spectrogram.compute_sgram_mmap import ComputeSpectrogramMmap
from core.spectrogram.entity.spectrogram import Spectrogram
from core.spectrogram.entity.spectrogram_mmap import SpectrogramMmap
from res.constants import MAX_SGRAM_LENGTH
from ui.base.view_model import ViewModel
from ui.document.state.audio_channel_state import AudioChannelState
from ui.document.state.load_progress_state import LoadProgressState
from ui.spectrogram.spectrogram_state import SpectrogramState


class SpectrogramViewModel(ViewModel):
    def __init__(self):
        super().__init__()
        self.sgram_state: SpectrogramState = SpectrogramState()

        self._buffer_generation = 0

    def compute_spectrogram(self, channel: AudioChannelState, start: float, end: float):
        x, t, fs = channel.x, channel.t, channel.fs

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
                self.state_changed.emit(self.sgram_state)

            use_case = ComputeSpectrogram(x[start:end], fs)
            self.launch_use_case("sgram_window", use_case, on_success, self.on_error)

    def load_spectrogram_mmap(self, x, fs):
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

    def invalidate_spectrogram(self):
        self._buffer_generation += 1
        self.close_thread("sgram_mmap")
        self.close_thread("sgram_window")
        self.sgram_state = replace(
            self.sgram_state, sxx_mmap=None, t_mmap=None, frames_computed=0
        )

    @pyqtSlot(object)
    def on_error(self, err):
        print(err)
