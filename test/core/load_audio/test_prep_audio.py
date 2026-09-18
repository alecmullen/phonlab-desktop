import numpy as np
import pytest

import core.load_audio.prep_audio as prep_audio_module
from core.load_audio.entity.audio_signal import AudioSignal
from core.load_audio.prep_audio import PrepAudio


def make_fake_prep_audio(
    monkeypatch: pytest.MonkeyPatch, return_fs: int = 8000
) -> list:
    calls = []

    def fake_prep_audio(
        x: np.ndarray,
        fs: int,
        target_fs: int,
        scale: bool,
        pre: float,
        add_tiny_noise: bool,
    ) -> tuple[np.ndarray, int]:
        calls.append(
            {
                "x": x,
                "fs": fs,
                "target_fs": target_fs,
                "scale": scale,
                "pre": pre,
                "add_tiny_noise": add_tiny_noise,
            }
        )
        return x * 2, return_fs

    monkeypatch.setattr(prep_audio_module.phon, "prep_audio", fake_prep_audio)
    return calls


def test_invoke_preps_each_retained_channel(monkeypatch: pytest.MonkeyPatch):
    calls = make_fake_prep_audio(monkeypatch, return_fs=8000)
    raw_signals = {
        0: AudioSignal(np.array([1.0, 2.0]), 16000),
        1: AudioSignal(np.array([3.0, 4.0]), 16000),
    }
    use_case = PrepAudio(
        raw_signals, target_fs=8000, retained_channels=[0, 1], pre=0.94
    )

    result = use_case.run_sync()

    assert result.keys() == {0, 1}
    np.testing.assert_array_equal(result[0].x, [2.0, 4.0])
    assert result[0].fs == 8000
    np.testing.assert_array_equal(result[1].x, [6.0, 8.0])
    assert result[1].fs == 8000
    assert [c["pre"] for c in calls] == [0.94, 0.94]
    assert [c["scale"] for c in calls] == [True, True]
    assert [c["add_tiny_noise"] for c in calls] == [True, True]
    assert [c["target_fs"] for c in calls] == [8000, 8000]
    assert [c["fs"] for c in calls] == [16000, 16000]


def test_invoke_only_processes_retained_channels(monkeypatch: pytest.MonkeyPatch):
    calls = make_fake_prep_audio(monkeypatch)
    raw_signals = {
        0: AudioSignal(np.array([1.0]), 16000),
        1: AudioSignal(np.array([2.0]), 16000),
        2: AudioSignal(np.array([3.0]), 16000),
    }
    use_case = PrepAudio(raw_signals, target_fs=8000, retained_channels=[2])

    result = use_case.run_sync()

    assert result.keys() == {2}
    assert len(calls) == 1


def test_invoke_defaults_pre_to_zero(monkeypatch: pytest.MonkeyPatch):
    calls = make_fake_prep_audio(monkeypatch)
    raw_signals = {0: AudioSignal(np.array([1.0]), 16000)}
    use_case = PrepAudio(raw_signals, target_fs=8000, retained_channels=[0])

    use_case.run_sync()

    assert calls[0]["pre"] == 0


def test_run_sync_stops_before_processing_any_channel_when_already_stopped(
    monkeypatch: pytest.MonkeyPatch,
):
    calls = make_fake_prep_audio(monkeypatch)
    raw_signals = {0: AudioSignal(np.array([1.0]), 16000)}
    use_case = PrepAudio(raw_signals, target_fs=8000, retained_channels=[0])
    use_case.stop()

    with pytest.raises(StopIteration):
        use_case.run_sync()

    assert calls == []


def test_invoke_yields_empty_dict_when_no_retained_channels(
    monkeypatch: pytest.MonkeyPatch,
):
    calls = make_fake_prep_audio(monkeypatch)
    use_case = PrepAudio({}, target_fs=8000, retained_channels=[])
    use_case.stop()

    result = use_case.run_sync()

    assert result == {}
    assert calls == []


def test_stop_sets_should_stop_flag():
    use_case = PrepAudio({}, target_fs=8000, retained_channels=[])
    assert use_case.should_stop is False

    use_case.stop()

    assert use_case.should_stop is True
