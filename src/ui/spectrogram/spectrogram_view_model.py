from dataclasses import replace

import numpy as np
from PyQt6.QtCore import pyqtSlot

import phonlab as phon
from core.entity.spectrogram import Spectrogram
from core.entity.spectrogram_mmap import SpectrogramMmap
from core.usecase.compute_sgram import ComputeSpectrogram
from core.usecase.compute_sgram_mmap import ComputeSpectrogramMmap
from res.constants import MAX_SGRAM_LENGTH
from ui.base.view_model import ViewModel
from ui.spectrogram.spectrogram_state import SpectrogramState


class SpectrogramViewModel(ViewModel):
    def __init__(self):
        super().__init__()
        self.sgram_state: SpectrogramState = SpectrogramState()

    def compute_spectrogram(
        self, x: np.ndarray, t: np.ndarray, fs: int, start: float, end: float
    ):
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

            @pyqtSlot(object)
            def on_success(sgram: Spectrogram):
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

            @pyqtSlot(object)
            def on_success(sgram: SpectrogramMmap):
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

    def adjust_gray_scale(self, adjustment: float):
        gray_cutoff = self.sgram_state.gray_cutoff + adjustment
        gray_cutoff = max(0.0, min(0.7, gray_cutoff))
        self.sgram_state = replace(self.sgram_state, gray_cutoff=gray_cutoff)
        self.state_changed.emit(self.sgram_state)

    @pyqtSlot(object)
    def on_error(self, err):
        print(err)
