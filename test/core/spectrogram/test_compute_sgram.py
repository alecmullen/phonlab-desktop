import numpy as np
import pytest

import core.spectrogram.compute_sgram as compute_sgram_module
from core.spectrogram.compute_sgram import ComputeSpectrogram


def test_invoke_yields_spectrogram_built_from_phon_compute_sgram(
    monkeypatch: pytest.MonkeyPatch,
):
    calls = []

    def fake_compute_sgram(
        x: np.ndarray, fs: int, window_size: float, step_size: float, order: int
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        calls.append(
            {
                "x": x,
                "fs": fs,
                "window_size": window_size,
                "step_size": step_size,
                "order": order,
            }
        )
        return np.array([0.0, 1.0]), np.array([0.0, 100.0]), np.array([[1.0, 2.0]])

    monkeypatch.setattr(compute_sgram_module.phon, "compute_sgram", fake_compute_sgram)
    x = np.arange(10, dtype=np.float64)
    use_case = ComputeSpectrogram(
        x, fs=1000, window_size=0.02, step_size=0.005, order=8
    )

    result = use_case.run_sync()

    assert len(calls) == 1
    call = calls[0]
    assert call["x"] is x
    assert call["fs"] == 1000
    assert call["window_size"] == 0.02
    assert call["step_size"] == 0.005
    assert call["order"] == 8
    np.testing.assert_array_equal(result.t, [0.0, 1.0])
    np.testing.assert_array_equal(result.f, [0.0, 100.0])
    np.testing.assert_array_equal(result.sxx, [[1.0, 2.0]])


def test_invoke_uses_default_settings(monkeypatch: pytest.MonkeyPatch):
    calls = []

    def fake_compute_sgram(
        x: np.ndarray, fs: int, window_size: float, step_size: float, order: int
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        calls.append((window_size, step_size, order))
        return np.zeros(1), np.zeros(1), np.zeros((1, 1))

    monkeypatch.setattr(compute_sgram_module.phon, "compute_sgram", fake_compute_sgram)
    use_case = ComputeSpectrogram(np.zeros(4), fs=1000)

    use_case.run_sync()

    assert calls == [(0.008, 0.001, 9)]


def test_stop_is_a_noop():
    use_case = ComputeSpectrogram(np.zeros(4), fs=1000)

    use_case.stop()
