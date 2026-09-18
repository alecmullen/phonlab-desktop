from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

import core.save_audio.save_audio as save_audio_module
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
    use_case = SaveAudio("out.wav", raw_x, raw_fs=44100, target_fs=16000, scale=True)

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
        "out.wav", np.zeros(1), raw_fs=8000, target_fs=8000, scale=False
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
        str(path), np.zeros(5), raw_fs=44100, target_fs=16000, scale=True
    )

    use_case.invoke()

    assert path.exists()
    written_x, written_fs = sf.read(str(path))
    assert written_fs == 16000
    np.testing.assert_allclose(written_x, prepped_x, atol=1e-4)
