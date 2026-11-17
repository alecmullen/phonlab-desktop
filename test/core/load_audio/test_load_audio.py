import numpy as np
import pytest

import core.load_audio.load_audio as load_audio_module
from core.load_audio.load_audio import LoadAudio


def test_invoke_yields_audio_signal_per_channel(monkeypatch: pytest.MonkeyPatch):
    def fake_loadsig(filename: str) -> tuple[np.ndarray, np.ndarray, int]:
        assert filename == "sound.wav"
        return (np.array([1.0, 2.0]), np.array([3.0, 4.0]), 16000)

    monkeypatch.setattr(load_audio_module.phon, "loadsig", fake_loadsig)
    use_case = LoadAudio()

    result = use_case.run_sync("sound.wav")

    assert result.keys() == {0, 1}
    np.testing.assert_array_equal(result[0].x, [1.0, 2.0])
    assert result[0].fs == 16000
    np.testing.assert_array_equal(result[1].x, [3.0, 4.0])
    assert result[1].fs == 16000


def test_invoke_handles_single_channel(monkeypatch: pytest.MonkeyPatch):
    def fake_loadsig(filename: str) -> tuple[np.ndarray, int]:
        return (np.array([5.0, 6.0, 7.0]), 8000)

    monkeypatch.setattr(load_audio_module.phon, "loadsig", fake_loadsig)
    use_case = LoadAudio()

    result = use_case.run_sync("mono.wav")

    assert result.keys() == {0}
    np.testing.assert_array_equal(result[0].x, [5.0, 6.0, 7.0])
    assert result[0].fs == 8000


def test_invoke_loads_several_files_as_channels(monkeypatch: pytest.MonkeyPatch):
    channels = {
        "a_L.wav": np.array([1.0, 2.0, 3.0]),
        "a_R.wav": np.array([4.0, 5.0]),
    }

    def fake_loadsig(filename: str) -> tuple[np.ndarray, int]:
        return (channels[filename], 8000)

    monkeypatch.setattr(load_audio_module.phon, "loadsig", fake_loadsig)

    result = LoadAudio().run_sync(["a_L.wav", "a_R.wav"])

    assert result.keys() == {0, 1}
    np.testing.assert_array_equal(result[0].x, [1.0, 2.0, 3.0])
    np.testing.assert_array_equal(result[1].x, [4.0, 5.0, 0.0])  # padded
    assert result[1].fs == 8000


def test_invoke_takes_the_first_channel_of_each_channel_file(
    monkeypatch: pytest.MonkeyPatch,
):
    def fake_loadsig(filename: str) -> tuple[np.ndarray, np.ndarray, int]:
        return (np.array([1.0]), np.array([9.0]), 8000)

    monkeypatch.setattr(load_audio_module.phon, "loadsig", fake_loadsig)

    result = LoadAudio().run_sync(["a.wav", "b.wav"])

    np.testing.assert_array_equal(result[1].x, [1.0])


def test_invoke_rejects_channel_files_with_different_sample_rates(
    monkeypatch: pytest.MonkeyPatch,
):
    rates = {"a.wav": 8000, "b.wav": 16000}

    def fake_loadsig(filename: str) -> tuple[np.ndarray, int]:
        return (np.array([1.0]), rates[filename])

    monkeypatch.setattr(load_audio_module.phon, "loadsig", fake_loadsig)

    with pytest.raises(ValueError):
        LoadAudio().run_sync(["a.wav", "b.wav"])
