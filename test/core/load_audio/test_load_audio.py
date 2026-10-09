import numpy as np
import pytest

import core.load_audio.load_audio as load_audio_module
from core.load_audio.load_audio import LoadAudio


def test_invoke_yields_audio_signal_per_channel(monkeypatch: pytest.MonkeyPatch):
    def fake_loadsig(filename: str) -> tuple[np.ndarray, np.ndarray, int]:
        assert filename == "sound.wav"
        return (np.array([1.0, 2.0]), np.array([3.0, 4.0]), 16000)

    monkeypatch.setattr(load_audio_module.phon, "loadsig", fake_loadsig)
    use_case = LoadAudio("sound.wav")

    result = use_case.run_sync()

    assert result.keys() == {0, 1}
    np.testing.assert_array_equal(result[0].x, [1.0, 2.0])
    assert result[0].fs == 16000
    np.testing.assert_array_equal(result[1].x, [3.0, 4.0])
    assert result[1].fs == 16000


def test_invoke_handles_single_channel(monkeypatch: pytest.MonkeyPatch):
    def fake_loadsig(filename: str) -> tuple[np.ndarray, int]:
        return (np.array([5.0, 6.0, 7.0]), 8000)

    monkeypatch.setattr(load_audio_module.phon, "loadsig", fake_loadsig)
    use_case = LoadAudio("mono.wav")

    result = use_case.run_sync()

    assert result.keys() == {0}
    np.testing.assert_array_equal(result[0].x, [5.0, 6.0, 7.0])
    assert result[0].fs == 8000


def test_stop_is_a_noop():
    use_case = LoadAudio("sound.wav")

    use_case.stop()
