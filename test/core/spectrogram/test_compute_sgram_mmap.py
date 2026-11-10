from pathlib import Path

import numpy as np
import pytest

import core.spectrogram.compute_sgram_mmap as compute_sgram_mmap_module
from core.spectrogram.compute_sgram_mmap import ComputeSpectrogramMmap


@pytest.fixture(autouse=True)
def mmap_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep the memmap backing files out of the real temp dir"""
    monkeypatch.setattr(
        compute_sgram_mmap_module.tempfile, "gettempdir", lambda: str(tmp_path)
    )
    return tmp_path


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


# --------------------------- estimate_resolution ---------------------------


def test_estimate_resolution_reports_freq_bins_and_frame_rate(
    monkeypatch: pytest.MonkeyPatch,
):
    make_fake_compute_sgram(monkeypatch, n_freqs=4)

    n_freqs, frames_per_sec = ComputeSpectrogramMmap().estimate_resolution(
        np.zeros(12, dtype=np.float64), fs=100
    )

    assert n_freqs == 4
    assert frames_per_sec == pytest.approx(100.0)


def test_estimate_resolution_probes_with_at_most_one_second_of_audio(
    monkeypatch: pytest.MonkeyPatch,
):
    calls = make_fake_compute_sgram(monkeypatch)

    ComputeSpectrogramMmap().estimate_resolution(
        np.zeros(500, dtype=np.float64), fs=100
    )

    assert len(calls) == 1
    assert calls[0]["len_x"] == 100


# --------------------------- init_mmap ---------------------------


def test_init_mmap_creates_correctly_shaped_memmaps(mmap_dir: Path):
    sxx_mmap, t_mmap = ComputeSpectrogramMmap().init_mmap(
        str(mmap_dir / "sxx.dat"),
        str(mmap_dir / "t.dat"),
        n_freqs=4,
        estimated_frames=14,
    )

    assert sxx_mmap.shape == (4, 14)
    assert t_mmap.shape == (14,)
    assert (mmap_dir / "sxx.dat").exists()
    assert (mmap_dir / "t.dat").exists()


def test_init_mmap_wraps_memory_error(monkeypatch: pytest.MonkeyPatch, mmap_dir: Path):
    def raise_memory_error(*args: object, **kwargs: object) -> None:
        raise MemoryError("no room")

    monkeypatch.setattr(compute_sgram_mmap_module.np, "memmap", raise_memory_error)

    with pytest.raises(MemoryError, match="Failed to create memory-mapped file"):
        ComputeSpectrogramMmap().init_mmap(
            str(mmap_dir / "sxx.dat"), str(mmap_dir / "t.dat"), 4, 14
        )


# --------------------------- __call__ ---------------------------


def run_in_chunks(x_len: int = 12) -> list:
    """Run the use case over `x_len` samples at 100Hz in 5-sample chunks"""
    return list(
        ComputeSpectrogramMmap()(
            np.zeros(x_len, dtype=np.float64), fs=100, chunk_duration=0.05
        )
    )


def test_call_yields_progressive_snapshots_per_chunk(
    monkeypatch: pytest.MonkeyPatch,
):
    make_fake_compute_sgram(monkeypatch)

    snapshots = run_in_chunks()

    assert [s.frames_computed for s in snapshots] == [5, 10, 12]
    assert [s.samples_computed for s in snapshots] == [5, 10, 12]
    assert all(s.frames_per_sec == pytest.approx(100.0) for s in snapshots)
    assert all(s.sxx_mmap is snapshots[0].sxx_mmap for s in snapshots)
    assert all(s.t_mmap is snapshots[0].t_mmap for s in snapshots)


def test_call_writes_each_chunk_into_its_own_mmap_slice(
    monkeypatch: pytest.MonkeyPatch,
):
    make_fake_compute_sgram(monkeypatch)

    sxx_mmap = run_in_chunks()[-1].sxx_mmap

    # the probe call is #1, so chunk writes are calls #2, #3, #4
    assert np.all(sxx_mmap[:, 0:5] == 2.0)
    assert np.all(sxx_mmap[:, 5:10] == 3.0)
    assert np.all(sxx_mmap[:, 10:12] == 4.0)


def test_call_offsets_chunk_times_by_chunk_start(monkeypatch: pytest.MonkeyPatch):
    make_fake_compute_sgram(monkeypatch)

    t_mmap = run_in_chunks()[-1].t_mmap

    # step_size defaults to 0.001, so the fake's raw t is [0, .001, .002, ...]
    np.testing.assert_allclose(t_mmap[0:5], np.arange(5) * 0.001 + 0 / 100)
    np.testing.assert_allclose(t_mmap[5:10], np.arange(5) * 0.001 + 5 / 100)
    np.testing.assert_allclose(t_mmap[10:12], np.arange(2) * 0.001 + 10 / 100)


def test_call_raises_runtime_error_and_cleans_up_on_chunk_failure(
    monkeypatch: pytest.MonkeyPatch, mmap_dir: Path
):
    probe = make_fake_compute_sgram(monkeypatch)
    real_fake = compute_sgram_mmap_module.phon.compute_sgram

    def fail_after_probe(*args: object, **kwargs: object) -> tuple:
        if probe:  # the resolution probe already ran: this is a chunk
            raise ValueError("boom")
        return real_fake(*args, **kwargs)

    monkeypatch.setattr(
        compute_sgram_mmap_module.phon, "compute_sgram", fail_after_probe
    )

    with pytest.raises(RuntimeError, match="Error during spectrogram computation"):
        run_in_chunks()

    assert list(mmap_dir.glob("*.dat")) == []


# --------------------------- cleanup ---------------------------


def test_closing_the_generator_removes_the_mmap_files(
    monkeypatch: pytest.MonkeyPatch, mmap_dir: Path
):
    make_fake_compute_sgram(monkeypatch)
    task = ComputeSpectrogramMmap()(
        np.zeros(12, dtype=np.float64), fs=100, chunk_duration=0.05
    )
    next(task)
    assert len(list(mmap_dir.glob("*.dat"))) == 2

    task.close()

    assert list(mmap_dir.glob("*.dat")) == []


def test_cleanup_mmaps_removes_files(mmap_dir: Path):
    use_case = ComputeSpectrogramMmap()
    mmap_file, ts_file = str(mmap_dir / "sxx.dat"), str(mmap_dir / "t.dat")
    sxx_mmap, t_mmap = use_case.init_mmap(mmap_file, ts_file, 4, 14)

    use_case.cleanup_mmaps(sxx_mmap, t_mmap, mmap_file, ts_file)

    assert list(mmap_dir.glob("*.dat")) == []


def test_cleanup_mmaps_is_safe_when_files_are_missing(mmap_dir: Path):
    ComputeSpectrogramMmap().cleanup_mmaps(
        None, None, str(mmap_dir / "gone.dat"), str(mmap_dir / "gone_t.dat")
    )
