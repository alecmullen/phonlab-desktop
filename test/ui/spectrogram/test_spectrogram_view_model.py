from dataclasses import replace
from typing import ClassVar

import numpy as np
import pytest
from PyQt6.QtCore import QObject, pyqtSignal
from pytestqt.qtbot import QtBot

import ui.base.view_model as view_model_module
import ui.spectrogram.spectrogram_view_model as svm_module
from core.load_audio.entity.audio_signal import AudioSignal
from core.spectrogram.entity.spectrogram import Spectrogram
from core.spectrogram.entity.spectrogram_mmap import SpectrogramMmap
from ui.base.state import State
from ui.document.state.audio_channel_state import AudioChannelState
from ui.document.state.load_progress_state import LoadProgressState
from ui.spectrogram.spectrogram_view_model import SpectrogramViewModel
from ui.spectrogram.state.audio_prepped import AudioPrepped
from ui.spectrogram.state.spectrogram_window_state import SpectrogramWindowState


class FakeJobManagerSignals(QObject):
    finished = pyqtSignal()


class FakeJobManager:
    def __init__(self):
        self.signals = FakeJobManagerSignals()
        self.jobs = []

    def __call__(self, job: object):
        self.jobs.append(job)

    def queue_job(self, job: object):
        self.jobs.append(job)

    def quit(self):
        pass


class FakeComputeSpectrogram:
    instances: ClassVar[list["FakeComputeSpectrogram"]] = []
    result: ClassVar[Spectrogram] = Spectrogram(
        t=np.array([0.0, 1.0]), f=np.array([0.0, 100.0]), sxx=np.array([[1.0, 2.0]])
    )

    def __init__(
        self,
        x: np.ndarray,
        fs: int,
        window_size: float,
        step_size: float,
        order: int,
    ):
        self.x = x
        self.fs = fs
        self.window_size = window_size
        self.step_size = step_size
        self.order = order
        FakeComputeSpectrogram.instances.append(self)

    def run_sync(self) -> Spectrogram:
        return FakeComputeSpectrogram.result


@pytest.fixture
def fake_job_manager(monkeypatch: pytest.MonkeyPatch) -> type[FakeJobManager]:
    monkeypatch.setattr(view_model_module, "JobManager", FakeJobManager)
    return FakeJobManager


@pytest.fixture
def fake_compute_spectrogram(
    monkeypatch: pytest.MonkeyPatch,
) -> type[FakeComputeSpectrogram]:
    FakeComputeSpectrogram.instances = []
    monkeypatch.setattr(svm_module, "ComputeSpectrogram", FakeComputeSpectrogram)
    return FakeComputeSpectrogram


# --------------------------- on_state_changed ---------------------------


def test_on_state_changed_loads_spectrogram_when_prepped_and_showing(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = SpectrogramViewModel()
    view_model.sgram_state = replace(view_model.sgram_state, is_showing=True)
    calls = []
    view_model.load_spectrogram = lambda: calls.append(True)

    view_model.on_state_changed(AudioPrepped())

    assert calls == [True]


def test_on_state_changed_does_not_load_when_not_showing(qtbot: QtBot):
    view_model = SpectrogramViewModel()
    calls = []
    view_model.load_spectrogram = lambda: calls.append(True)

    view_model.on_state_changed(AudioPrepped())

    assert calls == []


def test_on_state_changed_ignores_other_states(qtbot: QtBot):
    view_model = SpectrogramViewModel()
    view_model.sgram_state = replace(view_model.sgram_state, is_showing=True)
    calls = []
    view_model.load_spectrogram = lambda: calls.append(True)

    view_model.on_state_changed(State())

    assert calls == []


# --------------------------- prep_audio ---------------------------


def test_prep_audio_uses_settings_fs_when_target_not_given(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = SpectrogramViewModel()
    view_model.spectrogram_settings = replace(view_model.spectrogram_settings, fs=8000)

    view_model.prep_audio(np.arange(1000, dtype=np.float64), 1000)

    assert view_model.spectrogram_settings.fs == 8000
    np.testing.assert_array_equal(
        view_model.raw_audio_state.x, np.arange(1000, dtype=np.float64)
    )
    assert view_model.raw_audio_state.fs == 1000


def test_prep_audio_updates_settings_fs_when_target_given(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = SpectrogramViewModel()

    view_model.prep_audio(np.arange(1000, dtype=np.float64), 1000, target_fs=22050)

    assert view_model.spectrogram_settings.fs == 22050


def test_prep_audio_emits_load_progress_true(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = SpectrogramViewModel()
    received = []
    view_model.subscribe(received.append)

    view_model.prep_audio(np.arange(1000, dtype=np.float64), 1000)

    assert any(isinstance(s, LoadProgressState) and s.is_loading for s in received)


def test_prep_audio_on_success_updates_prepped_state_and_emits_audio_prepped(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = SpectrogramViewModel()
    received = []
    view_model.subscribe(received.append)
    view_model.load_spectrogram = lambda: None

    view_model.prep_audio(np.arange(1000, dtype=np.float64), 1000)

    manager = view_model.job_managers["prep_audio"]
    job = manager.jobs[0]
    prepped = {0: AudioSignal(np.arange(2000, dtype=np.float64), 16000)}

    job.on_success(prepped)

    np.testing.assert_array_equal(
        view_model.prepped_audio_state.x, np.arange(2000, dtype=np.float64)
    )
    assert view_model.prepped_audio_state.fs == 16000
    assert any(isinstance(s, LoadProgressState) and not s.is_loading for s in received)
    assert any(isinstance(s, AudioPrepped) for s in received)


def test_prep_audio_on_success_invalidates_spectrogram(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = SpectrogramViewModel()
    view_model.sgram_state = replace(
        view_model.sgram_state, sxx_mmap=np.zeros((1, 1)), t_mmap=np.zeros(1)
    )
    generation_before = view_model._buffer_generation

    view_model.prep_audio(np.arange(1000, dtype=np.float64), 1000)
    manager = view_model.job_managers["prep_audio"]
    job = manager.jobs[0]
    job.on_success({0: AudioSignal(np.arange(2000, dtype=np.float64), 16000)})

    assert view_model._buffer_generation == generation_before + 1
    assert view_model.sgram_state.sxx_mmap is None
    assert view_model.sgram_state.t_mmap is None


# --------------------------- load_spectrogram ---------------------------


def test_load_spectrogram_returns_early_when_no_prepped_audio(qtbot: QtBot):
    view_model = SpectrogramViewModel()

    view_model.load_spectrogram()

    assert view_model.sgram_state.is_loading is True
    assert view_model.sgram_state.is_showing is False


def test_load_spectrogram_hides_when_window_too_long(qtbot: QtBot):
    view_model = SpectrogramViewModel()
    fs = 1000
    view_model.prepped_audio_state = AudioChannelState(
        np.arange(fs * 20, dtype=np.float64), fs
    )
    view_model.window_state = SpectrogramWindowState(0, fs * 11)
    received = []
    view_model.subscribe(received.append)

    view_model.load_spectrogram()

    assert view_model.sgram_state.is_showing is False
    assert view_model.sgram_state.is_loading is False
    assert received[-1] is view_model.sgram_state


def test_load_spectrogram_hides_when_window_too_short(qtbot: QtBot):
    view_model = SpectrogramViewModel()
    fs = 1000
    view_model.prepped_audio_state = AudioChannelState(
        np.arange(fs * 5, dtype=np.float64), fs
    )
    window_samples = int(view_model.spectrogram_settings.window_size * fs)
    view_model.window_state = SpectrogramWindowState(0, window_samples - 1)

    view_model.load_spectrogram()

    assert view_model.sgram_state.is_showing is False
    assert view_model.sgram_state.is_loading is False


def test_load_spectrogram_loads_window_and_computes_mmap_when_missing(
    qtbot: QtBot,
):
    view_model = SpectrogramViewModel()
    fs = 1000
    view_model.prepped_audio_state = AudioChannelState(
        np.arange(fs * 5, dtype=np.float64), fs
    )
    view_model.window_state = SpectrogramWindowState(0, fs * 2)

    window_calls = []
    view_model.load_spectrogram_window = lambda x, t, fs, start, end: (
        window_calls.append((start, end))
    )
    mmap_calls = []
    view_model.compute_spectrogram_mmap = lambda x, fs: mmap_calls.append((len(x), fs))

    view_model.load_spectrogram()

    assert window_calls == [(0, fs * 2)]
    assert mmap_calls == [(fs * 5, fs)]


def test_load_spectrogram_skips_mmap_computation_when_already_present(
    qtbot: QtBot,
):
    view_model = SpectrogramViewModel()
    fs = 1000
    view_model.prepped_audio_state = AudioChannelState(
        np.arange(fs * 5, dtype=np.float64), fs
    )
    view_model.window_state = SpectrogramWindowState(0, fs * 2)
    view_model.sgram_state = replace(
        view_model.sgram_state, sxx_mmap=np.zeros((1, 1)), t_mmap=np.zeros(1)
    )

    view_model.load_spectrogram_window = lambda *args: None
    mmap_calls = []
    view_model.compute_spectrogram_mmap = lambda x, fs: mmap_calls.append(True)

    view_model.load_spectrogram()

    assert mmap_calls == []


# --------------------------- load_spectrogram_window ---------------------------


def test_load_spectrogram_window_uses_cached_mmap_when_available(qtbot: QtBot):
    view_model = SpectrogramViewModel()
    fs = 1000
    t = np.arange(10, dtype=np.float64) / fs
    t_mmap = np.array([0.0, 0.001, 0.003, 0.005, 0.007, 0.009])
    sxx_mmap = np.arange(6.0).reshape(1, 6)
    view_model.sgram_state = replace(
        view_model.sgram_state,
        sxx_mmap=sxx_mmap,
        t_mmap=t_mmap,
        frames_computed=6,
        samples_computed=10,
    )
    received = []
    view_model.subscribe(received.append)

    view_model.load_spectrogram_window(np.zeros(10), t, fs, 2, 8)

    assert view_model.sgram_state.is_showing is True
    np.testing.assert_array_equal(view_model.sgram_state.t_window, t_mmap[2:5])
    np.testing.assert_array_equal(view_model.sgram_state.sxx_window, sxx_mmap[:, 2:5])
    assert received[-1] is view_model.sgram_state


def test_load_spectrogram_window_computes_fresh_when_no_cache(qtbot: QtBot):
    view_model = SpectrogramViewModel()
    fs = 1000
    t = np.arange(10, dtype=np.float64) / fs

    low_res_calls = []
    view_model.compute_low_res_sgram = lambda x, fs, start, end: low_res_calls.append(
        (start, end)
    )
    window_calls = []
    view_model.compute_sgram_window = lambda x, fs, start, end: window_calls.append(
        (start, end)
    )

    view_model.load_spectrogram_window(np.zeros(10), t, fs, 2, 8)

    assert low_res_calls == [(2, 8)]
    assert window_calls == [(2, 8)]


def test_load_spectrogram_window_computes_fresh_when_window_extends_past_computed(
    qtbot: QtBot,
):
    view_model = SpectrogramViewModel()
    fs = 1000
    t = np.arange(10, dtype=np.float64) / fs
    view_model.sgram_state = replace(
        view_model.sgram_state,
        sxx_mmap=np.zeros((1, 6)),
        t_mmap=np.zeros(6),
        frames_computed=6,
        samples_computed=5,
    )

    low_res_calls = []
    view_model.compute_low_res_sgram = lambda x, fs, start, end: low_res_calls.append(
        True
    )
    view_model.compute_sgram_window = lambda x, fs, start, end: None

    view_model.load_spectrogram_window(np.zeros(10), t, fs, 2, 8)

    assert low_res_calls == [True]


# --------------------------- compute_low_res_sgram ---------------------------


def test_compute_low_res_sgram_updates_window_state(
    qtbot: QtBot, fake_compute_spectrogram: type[FakeComputeSpectrogram]
):
    view_model = SpectrogramViewModel()
    x = np.arange(1000, dtype=np.float64)

    view_model.compute_low_res_sgram(x, 1000, 100, 500)

    instance = fake_compute_spectrogram.instances[0]
    assert instance.step_size == 0.003
    # SpectrogramSettingsState.__post_init__ raises order 7 to the minimum (8)
    # required for the default window_size/fs.
    assert instance.order == 8
    np.testing.assert_array_equal(instance.x, x[100:500])

    np.testing.assert_array_equal(
        view_model.sgram_state.t_window,
        FakeComputeSpectrogram.result.t + (100 / 1000),
    )
    np.testing.assert_array_equal(
        view_model.sgram_state.sxx_window, FakeComputeSpectrogram.result.sxx
    )
    assert view_model.sgram_state.is_showing is True


# --------------------------- compute_sgram_window ---------------------------


def test_compute_sgram_window_updates_state_on_success(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = SpectrogramViewModel()
    x = np.arange(1000, dtype=np.float64)

    view_model.compute_sgram_window(x, 1000, 100, 500)

    manager = view_model.job_managers["sgram_window"]
    job = manager.jobs[0]
    sgram = Spectrogram(
        t=np.array([0.0, 0.1]), f=np.array([0.0, 50.0]), sxx=np.array([[1.0, 2.0]])
    )

    job.on_success(sgram)

    np.testing.assert_array_equal(
        view_model.sgram_state.t_window, sgram.t + (100 / 1000)
    )
    np.testing.assert_array_equal(view_model.sgram_state.sxx_window, sgram.sxx)
    assert view_model.sgram_state.is_showing is True


def test_compute_sgram_window_ignores_stale_generation(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = SpectrogramViewModel()
    x = np.arange(1000, dtype=np.float64)

    view_model.compute_sgram_window(x, 1000, 100, 500)
    manager = view_model.job_managers["sgram_window"]
    job = manager.jobs[0]

    view_model._buffer_generation += 1
    sgram = Spectrogram(t=np.array([0.0]), f=np.array([0.0]), sxx=np.array([[1.0]]))
    job.on_success(sgram)

    assert view_model.sgram_state.is_showing is False


# --------------------------- compute_spectrogram_mmap ---------------------------


def test_compute_spectrogram_mmap_updates_state_on_success(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = SpectrogramViewModel()
    x = np.arange(1000, dtype=np.float64)

    view_model.compute_spectrogram_mmap(x, 1000)

    manager = view_model.job_managers["sgram_mmap"]
    job = manager.jobs[0]
    sgram = SpectrogramMmap(
        t_mmap=np.array([0.0, 0.1]),
        sxx_mmap=np.array([[1.0, 5.0]]),
        frames_per_sec=100.0,
        frames_computed=2,
        samples_computed=200,
    )

    job.on_success(sgram)

    assert view_model.sgram_state.frames_computed == 2
    assert view_model.sgram_state.samples_computed == 200
    assert view_model.sgram_state.frames_per_sec == 100.0
    assert view_model.sgram_state.max_sxx == 5.0
    assert view_model.sgram_state.min_sxx == 1.0


def test_compute_spectrogram_mmap_launches_only_once(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = SpectrogramViewModel()
    x = np.arange(1000, dtype=np.float64)

    view_model.compute_spectrogram_mmap(x, 1000)
    view_model.compute_spectrogram_mmap(x, 1000)

    manager = view_model.job_managers["sgram_mmap"]
    assert len(manager.jobs) == 1


def test_compute_spectrogram_mmap_ignores_stale_generation(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = SpectrogramViewModel()
    x = np.arange(1000, dtype=np.float64)

    view_model.compute_spectrogram_mmap(x, 1000)
    manager = view_model.job_managers["sgram_mmap"]
    job = manager.jobs[0]

    view_model._buffer_generation += 1
    sgram = SpectrogramMmap(
        t_mmap=np.array([0.0]),
        sxx_mmap=np.array([[1.0]]),
        frames_per_sec=100.0,
        frames_computed=1,
        samples_computed=100,
    )
    job.on_success(sgram)

    assert view_model.sgram_state.frames_computed == 0


# --------------------------- adjust_gray_scale ---------------------------


def test_adjust_gray_scale_applies_adjustment(qtbot: QtBot):
    view_model = SpectrogramViewModel()
    view_model.sgram_state = replace(view_model.sgram_state, gray_cutoff=0.3)
    received = []
    view_model.subscribe(received.append)

    view_model.adjust_gray_scale(0.1)

    assert view_model.sgram_state.gray_cutoff == pytest.approx(0.4)
    assert received[-1] is view_model.sgram_state


def test_adjust_gray_scale_clamps_to_upper_bound(qtbot: QtBot):
    view_model = SpectrogramViewModel()
    view_model.sgram_state = replace(view_model.sgram_state, gray_cutoff=0.65)

    view_model.adjust_gray_scale(0.5)

    assert view_model.sgram_state.gray_cutoff == 0.7


def test_adjust_gray_scale_clamps_to_lower_bound(qtbot: QtBot):
    view_model = SpectrogramViewModel()
    view_model.sgram_state = replace(view_model.sgram_state, gray_cutoff=0.05)

    view_model.adjust_gray_scale(-0.5)

    assert view_model.sgram_state.gray_cutoff == 0.0


# --------------------------- update_sxx_extrema ---------------------------


def test_update_sxx_extrema_tracks_min_and_max_across_calls(qtbot: QtBot):
    view_model = SpectrogramViewModel()

    view_model.update_sxx_extrema(np.array([1.0, 5.0, 3.0]))
    view_model.update_sxx_extrema(np.array([-2.0, 4.0]))

    assert view_model.sgram_state.min_sxx == -2.0
    assert view_model.sgram_state.max_sxx == 5.0


# --------------------------- invalidate_spectrogram ---------------------------


def test_invalidate_spectrogram_increments_generation_and_clears_mmap(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = SpectrogramViewModel()
    generation_before = view_model._buffer_generation
    view_model.sgram_state = replace(
        view_model.sgram_state,
        sxx_mmap=np.zeros((1, 1)),
        t_mmap=np.zeros(1),
        frames_computed=5,
    )
    view_model.compute_spectrogram_mmap(np.arange(10, dtype=np.float64), 1000)

    view_model.invalidate_spectrogram()

    assert view_model._buffer_generation == generation_before + 1
    assert view_model.sgram_state.sxx_mmap is None
    assert view_model.sgram_state.t_mmap is None
    assert view_model.sgram_state.frames_computed == 0
    assert "sgram_mmap" not in view_model.job_managers


# --------------------------- set_window_state ---------------------------


def test_set_window_state_converts_sample_indices_and_loads(qtbot: QtBot):
    view_model = SpectrogramViewModel()
    view_model.spectrogram_settings = replace(view_model.spectrogram_settings, fs=2000)
    load_calls = []
    view_model.load_spectrogram = lambda: load_calls.append(True)

    view_model.set_window_state(start=0, end=1000, raw_fs=1000)

    assert view_model.window_state == SpectrogramWindowState(0, 2000)
    assert load_calls == [True]


def test_set_window_state_updates_settings_fs_when_target_given(qtbot: QtBot):
    view_model = SpectrogramViewModel()
    view_model.load_spectrogram = lambda: None

    view_model.set_window_state(start=0, end=1000, raw_fs=1000, target_fs=4000)

    assert view_model.spectrogram_settings.fs == 4000
    assert view_model.window_state == SpectrogramWindowState(0, 4000)


# --------------------------- update_settings ---------------------------


def test_update_settings_returns_early_without_raw_audio(qtbot: QtBot):
    view_model = SpectrogramViewModel()
    new_settings = replace(view_model.spectrogram_settings, window_size=0.02)

    view_model.update_settings(new_settings)

    assert view_model.spectrogram_settings == new_settings


def test_update_settings_resamples_when_fs_changes(
    qtbot: QtBot, fake_job_manager: type[FakeJobManager]
):
    view_model = SpectrogramViewModel()
    view_model.raw_audio_state = AudioChannelState(
        np.arange(1000, dtype=np.float64), 1000
    )
    prep_calls = []
    view_model.prep_audio = lambda x, fs: prep_calls.append((len(x), fs))

    new_settings = replace(view_model.spectrogram_settings, fs=8000)
    view_model.update_settings(new_settings)

    assert prep_calls == [(1000, 1000)]


def test_update_settings_reloads_without_resample_when_fs_unchanged(
    qtbot: QtBot,
):
    view_model = SpectrogramViewModel()
    view_model.raw_audio_state = AudioChannelState(
        np.arange(1000, dtype=np.float64), 1000
    )
    invalidate_calls = []
    view_model.invalidate_spectrogram = lambda: invalidate_calls.append(True)
    load_calls = []
    view_model.load_spectrogram = lambda: load_calls.append(True)

    new_settings = replace(view_model.spectrogram_settings, window_size=0.02)
    view_model.update_settings(new_settings)

    assert invalidate_calls == [True]
    assert load_calls == [True]
    assert view_model.spectrogram_settings == new_settings


# --------------------------- on_error ---------------------------


def test_on_error_does_not_raise(qtbot: QtBot, capsys: pytest.CaptureFixture):
    view_model = SpectrogramViewModel()

    view_model.on_error(ValueError("boom"))

    assert "boom" in capsys.readouterr().out
