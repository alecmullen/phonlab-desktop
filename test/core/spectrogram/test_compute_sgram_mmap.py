import os

import numpy as np
import pytest

import core.spectrogram.compute_sgram_mmap as compute_sgram_mmap_module
from core.spectrogram.compute_sgram_mmap import ComputeSpectrogramMmap


def make_fake_compute_sgram(
    monkeypatch: pytest.MonkeyPatch, n_freqs: int = 4
) -> list[dict]:
    calls = []

    def fake_compute_sgram(
        x: np.ndarray, fs: int, window_size: float, step_size: float, order: int
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        calls.append(
            {
                "len_x": len(x),
                "fs": fs,
                "window_size": window_size,
                "step_size": step_size,
                "order": order,
            }
        )
        n_frames = max(1, len(x))
        t = np.arange(n_frames, dtype=np.float64) * step_size
        f = np.arange(n_freqs, dtype=np.float64)
        sxx = np.full((n_freqs, n_frames), float(len(calls)), dtype=np.float32)
        return t, f, sxx

    monkeypatch.setattr(
        compute_sgram_mmap_module.phon, "compute_sgram", fake_compute_sgram
    )
    return calls


# --------------------------- init_mmap ---------------------------


def test_init_mmap_creates_correctly_shaped_memmaps(monkeypatch: pytest.MonkeyPatch):
    make_fake_compute_sgram(monkeypatch, n_freqs=4)
    use_case = ComputeSpectrogramMmap(np.zeros(12, dtype=np.float64), fs=100)

    sxx_mmap, t_mmap, frames_per_sec, estimated_frames = use_case.init_mmap()

    assert sxx_mmap.shape == (4, estimated_frames)
    assert t_mmap.shape == (estimated_frames,)
    assert frames_per_sec == pytest.approx(100.0)
    assert estimated_frames == int(100.0 * (12 / 100) * 1.2)
    assert use_case.mmap_file is not None
    assert use_case.ts_file is not None


def test_init_mmap_probes_with_at_most_one_second_of_audio(
    monkeypatch: pytest.MonkeyPatch,
):
    calls = make_fake_compute_sgram(monkeypatch)
    use_case = ComputeSpectrogramMmap(np.zeros(500, dtype=np.float64), fs=100)

    use_case.init_mmap()

    assert len(calls) == 1
    assert calls[0]["len_x"] == 100


def test_init_mmap_wraps_memory_error(monkeypatch: pytest.MonkeyPatch):
    make_fake_compute_sgram(monkeypatch)

    def raise_memory_error(*args: object, **kwargs: object) -> None:
        raise MemoryError("no room")

    monkeypatch.setattr(compute_sgram_mmap_module.np, "memmap", raise_memory_error)
    use_case = ComputeSpectrogramMmap(np.zeros(10, dtype=np.float64), fs=100)

    with pytest.raises(MemoryError):
        use_case.init_mmap()


# --------------------------- invoke ---------------------------


def test_invoke_yields_progressive_snapshots_per_chunk(
    monkeypatch: pytest.MonkeyPatch,
):
    make_fake_compute_sgram(monkeypatch)
    use_case = ComputeSpectrogramMmap(
        np.zeros(12, dtype=np.float64), fs=100, chunk_duration=0.05
    )

    snapshots = list(use_case.invoke())

    assert [s.frames_computed for s in snapshots] == [5, 10, 12]
    assert [s.samples_computed for s in snapshots] == [5, 10, 12]
    assert all(s.frames_per_sec == pytest.approx(100.0) for s in snapshots)
    assert all(s.sxx_mmap is use_case.sxx_mmap for s in snapshots)
    assert all(s.t_mmap is use_case.t_mmap for s in snapshots)
    use_case.stop()


def test_invoke_writes_each_chunk_into_its_own_mmap_slice(
    monkeypatch: pytest.MonkeyPatch,
):
    make_fake_compute_sgram(monkeypatch)
    use_case = ComputeSpectrogramMmap(
        np.zeros(12, dtype=np.float64), fs=100, chunk_duration=0.05
    )

    list(use_case.invoke())

    # chunk 1 (probe call is #1, so chunk writes are calls #2, #3, #4)
    assert np.all(use_case.sxx_mmap[:, 0:5] == 2.0)
    assert np.all(use_case.sxx_mmap[:, 5:10] == 3.0)
    assert np.all(use_case.sxx_mmap[:, 10:12] == 4.0)
    use_case.stop()


def test_invoke_offsets_chunk_times_by_chunk_start(monkeypatch: pytest.MonkeyPatch):
    make_fake_compute_sgram(monkeypatch)
    use_case = ComputeSpectrogramMmap(
        np.zeros(12, dtype=np.float64), fs=100, chunk_duration=0.05
    )

    list(use_case.invoke())

    # step_size defaults to 0.001, so the fake's raw t is [0, .001, .002, ...]
    np.testing.assert_allclose(use_case.t_mmap[0:5], np.arange(5) * 0.001 + 0 / 100)
    np.testing.assert_allclose(use_case.t_mmap[5:10], np.arange(5) * 0.001 + 5 / 100)
    np.testing.assert_allclose(use_case.t_mmap[10:12], np.arange(2) * 0.001 + 10 / 100)
    use_case.stop()


def test_invoke_raises_runtime_error_and_cleans_up_on_chunk_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    def fake_compute_sgram(
        x: np.ndarray, fs: int, window_size: float, step_size: float, order: int
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if len(x) == 100:
            # the init_mmap probe call
            n_frames = 100
            return (
                np.arange(n_frames, dtype=np.float64),
                np.zeros(4),
                np.zeros((4, n_frames), dtype=np.float32),
            )
        raise ValueError("boom")

    monkeypatch.setattr(
        compute_sgram_mmap_module.phon, "compute_sgram", fake_compute_sgram
    )
    use_case = ComputeSpectrogramMmap(
        np.zeros(12, dtype=np.float64), fs=100, chunk_duration=0.05
    )

    with pytest.raises(RuntimeError, match="Error during spectrogram computation"):
        list(use_case.invoke())

    assert use_case.sxx_mmap is None
    assert use_case.t_mmap is None
    assert use_case.mmap_file is None
    assert use_case.ts_file is None


# --------------------------- stop ---------------------------


def test_stop_removes_mmap_files_and_clears_state(monkeypatch: pytest.MonkeyPatch):
    make_fake_compute_sgram(monkeypatch)
    use_case = ComputeSpectrogramMmap(
        np.zeros(12, dtype=np.float64), fs=100, chunk_duration=0.05
    )
    list(use_case.invoke())
    mmap_file = use_case.mmap_file
    ts_file = use_case.ts_file
    assert os.path.exists(mmap_file)
    assert os.path.exists(ts_file)

    use_case.stop()

    assert use_case.sxx_mmap is None
    assert use_case.t_mmap is None
    assert use_case.mmap_file is None
    assert use_case.ts_file is None
    assert not os.path.exists(mmap_file)
    assert not os.path.exists(ts_file)


def test_stop_is_safe_to_call_when_nothing_was_computed():
    use_case = ComputeSpectrogramMmap(np.zeros(12, dtype=np.float64), fs=100)

    use_case.stop()

    assert use_case.sxx_mmap is None
    assert use_case.t_mmap is None
