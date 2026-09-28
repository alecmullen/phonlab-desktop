from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

import core.save_audio.save_audio as save_audio_module
from core.load_audio.entity.audio_signal import AudioSignal
from core.save_audio.save_audio import SaveAudio


def test_invoke_preps_audio_and_writes_with_pcm16(monkeypatch: pytest.MonkeyPatch):
    prep_calls = []
    write_calls = []

    def fake_prep_audio(
        raw_x: np.ndarray,
        raw_fs: int,
        target_fs: int,
        scale: bool,
        pre: float,
        add_tiny_noise: bool,
    ) -> tuple[np.ndarray, int]:
        prep_calls.append(
            {
                "raw_x": raw_x,
                "raw_fs": raw_fs,
                "target_fs": target_fs,
                "scale": scale,
                "pre": pre,
                "add_tiny_noise": add_tiny_noise,
            }
        )
        return np.array([0.1, 0.2]), target_fs

    def fake_write(path: str, x: np.ndarray, fs: int, subtype: str) -> None:
        write_calls.append({"path": path, "x": x, "fs": fs, "subtype": subtype})

    monkeypatch.setattr(save_audio_module.phon, "prep_audio", fake_prep_audio)
    monkeypatch.setattr(save_audio_module.sf, "write", fake_write)

    raw_x = np.array([1.0, 2.0, 3.0])
    use_case = SaveAudio(
        "out.wav", [AudioSignal(raw_x, 44100)], target_fs=16000, scale=True
    )

    use_case.invoke()

    assert len(prep_calls) == 1
    call = prep_calls[0]
    assert call["raw_x"] is raw_x
    assert call["raw_fs"] == 44100
    assert call["target_fs"] == 16000
    assert call["scale"] is True
    assert call["pre"] == 0
    assert call["add_tiny_noise"] is False

    assert len(write_calls) == 1
    write_call = write_calls[0]
    assert write_call["path"] == "out.wav"
    np.testing.assert_array_equal(write_call["x"], [0.1, 0.2])
    assert write_call["x"].ndim == 1
    assert write_call["fs"] == 16000
    assert write_call["subtype"] == "PCM_16"


def test_invoke_passes_scale_false_through(monkeypatch: pytest.MonkeyPatch):
    scale_values = []

    def fake_prep_audio(
        raw_x: np.ndarray,
        raw_fs: int,
        target_fs: int,
        scale: bool,
        pre: float,
        add_tiny_noise: bool,
    ) -> tuple[np.ndarray, int]:
        scale_values.append(scale)
        return np.zeros(1), target_fs

    monkeypatch.setattr(save_audio_module.phon, "prep_audio", fake_prep_audio)
    monkeypatch.setattr(save_audio_module.sf, "write", lambda *args, **kwargs: None)

    use_case = SaveAudio(
        "out.wav", [AudioSignal(np.zeros(1), 8000)], target_fs=8000, scale=False
    )

    use_case.invoke()

    assert scale_values == [False]


def test_invoke_writes_prepped_audio_to_a_real_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    prepped_x = np.array([0.0, 0.5, -0.5, 1.0, -1.0], dtype=np.float64)

    def fake_prep_audio(
        raw_x: np.ndarray,
        raw_fs: int,
        target_fs: int,
        scale: bool,
        pre: float,
        add_tiny_noise: bool,
    ) -> tuple[np.ndarray, int]:
        return prepped_x, target_fs

    monkeypatch.setattr(save_audio_module.phon, "prep_audio", fake_prep_audio)

    path = tmp_path / "out.wav"
    use_case = SaveAudio(
        str(path), [AudioSignal(np.zeros(5), 44100)], target_fs=16000, scale=True
    )

    use_case.invoke()

    assert path.exists()
    written_x, written_fs = sf.read(str(path))
    assert written_fs == 16000
    np.testing.assert_allclose(written_x, prepped_x, atol=1e-4)


# --------------------------- stereo (two channels) ---------------------------


def test_invoke_writes_stereo_as_two_column_array(monkeypatch: pytest.MonkeyPatch):
    prepped_by_fs = {}

    def fake_prep_audio(
        raw_x: np.ndarray,
        raw_fs: int,
        target_fs: int,
        scale: bool,
        pre: float,
        add_tiny_noise: bool,
    ) -> tuple[np.ndarray, int]:
        prepped_by_fs.setdefault(raw_fs, np.asarray(raw_x) * 2)
        return prepped_by_fs[raw_fs], target_fs

    write_calls = []
    monkeypatch.setattr(save_audio_module.phon, "prep_audio", fake_prep_audio)
    monkeypatch.setattr(
        save_audio_module.sf,
        "write",
        lambda path, x, fs, subtype: write_calls.append(
            {"path": path, "x": x, "fs": fs, "subtype": subtype}
        ),
    )

    channel0 = AudioSignal(np.array([1.0, 2.0, 3.0]), 44100)
    channel1 = AudioSignal(np.array([4.0, 5.0, 6.0]), 48000)
    use_case = SaveAudio("out.wav", [channel0, channel1], target_fs=16000, scale=True)

    use_case.invoke()

    assert len(write_calls) == 1
    written = write_calls[0]["x"]
    assert written.ndim == 2
    assert written.shape == (3, 2)
    np.testing.assert_array_equal(written[:, 0], channel0.x * 2)
    np.testing.assert_array_equal(written[:, 1], channel1.x * 2)


def test_invoke_calls_prep_audio_once_per_channel_independently(
    monkeypatch: pytest.MonkeyPatch,
):
    calls = []

    def fake_prep_audio(
        raw_x: np.ndarray,
        raw_fs: int,
        target_fs: int,
        scale: bool,
        pre: float,
        add_tiny_noise: bool,
    ) -> tuple[np.ndarray, int]:
        calls.append({"raw_x": raw_x, "raw_fs": raw_fs, "target_fs": target_fs})
        return np.asarray(raw_x), target_fs

    monkeypatch.setattr(save_audio_module.phon, "prep_audio", fake_prep_audio)
    monkeypatch.setattr(save_audio_module.sf, "write", lambda *args, **kwargs: None)

    channel0 = AudioSignal(np.array([1.0, 2.0]), 44100)
    channel1 = AudioSignal(np.array([3.0, 4.0]), 48000)
    use_case = SaveAudio("out.wav", [channel0, channel1], target_fs=16000, scale=True)

    use_case.invoke()

    assert len(calls) == 2
    np.testing.assert_array_equal(calls[0]["raw_x"], channel0.x)
    assert calls[0]["raw_fs"] == 44100
    np.testing.assert_array_equal(calls[1]["raw_x"], channel1.x)
    assert calls[1]["raw_fs"] == 48000
    assert calls[0]["target_fs"] == calls[1]["target_fs"] == 16000


def test_invoke_writes_real_two_channel_wav_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    def fake_prep_audio(
        raw_x: np.ndarray,
        raw_fs: int,
        target_fs: int,
        scale: bool,
        pre: float,
        add_tiny_noise: bool,
    ) -> tuple[np.ndarray, int]:
        return np.asarray(raw_x, dtype=np.float64), target_fs

    monkeypatch.setattr(save_audio_module.phon, "prep_audio", fake_prep_audio)

    channel0 = AudioSignal(np.linspace(-1, 1, 100, dtype=np.float64), 16000)
    channel1 = AudioSignal(np.linspace(1, -1, 100, dtype=np.float64), 16000)
    path = tmp_path / "stereo_out.wav"

    use_case = SaveAudio(str(path), [channel0, channel1], target_fs=16000, scale=False)
    use_case.invoke()

    assert path.exists()
    written_x, written_fs = sf.read(str(path))
    assert written_fs == 16000
    assert written_x.ndim == 2
    assert written_x.shape[1] == 2
