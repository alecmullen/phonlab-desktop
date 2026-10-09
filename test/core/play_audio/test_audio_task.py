import types

import numpy as np
import pytest
import sounddevice as sd
from pytestqt.qtbot import QtBot

import core.play_audio.audio_task as audio_task_module
from core.play_audio.audio_task import AudioTask


def make_time_info(dac_time: float = 1.5, current_time: float = 1.0) -> object:
    return types.SimpleNamespace(outputBufferDacTime=dac_time, currentTime=current_time)


# --------------------------- __init__ ---------------------------


def test_init_adds_channel_dimension_for_1d_audio():
    task = AudioTask(np.array([1.0, 2.0, 3.0]), fs=1000)

    assert task._audio_data.shape == (3, 1)


def test_init_keeps_multichannel_audio_shape_unchanged():
    x = np.zeros((5, 2))

    task = AudioTask(x, fs=1000)

    assert task._audio_data.shape == (5, 2)


# --------------------------- _audio_callback ---------------------------


def test_audio_callback_emits_latency_on_first_chunk(qtbot: QtBot):
    task = AudioTask(np.zeros(10), fs=1000)
    received = []
    task.latency.connect(received.append)
    outdata = np.zeros((4, 1), dtype="float32")

    task._audio_callback(outdata, 4, make_time_info(1.5, 1.0), sd.CallbackFlags())

    assert len(received) == 1
    assert received[0].latency == pytest.approx(0.5)
    assert task._is_first_chunk is False


def test_audio_callback_does_not_emit_latency_on_subsequent_chunks(qtbot: QtBot):
    task = AudioTask(np.zeros(10), fs=1000)
    task._is_first_chunk = False
    received = []
    task.latency.connect(received.append)
    outdata = np.zeros((4, 1), dtype="float32")

    task._audio_callback(outdata, 4, make_time_info(), sd.CallbackFlags())

    assert received == []


def test_audio_callback_copies_full_frame_and_advances_offset(qtbot: QtBot):
    task = AudioTask(np.arange(10, dtype="float32"), fs=1000)
    task._is_first_chunk = False
    outdata = np.zeros((4, 1), dtype="float32")

    task._audio_callback(outdata, 4, make_time_info(), sd.CallbackFlags())

    np.testing.assert_array_equal(outdata[:, 0], [0, 1, 2, 3])
    assert task._current_offset == 4


def test_audio_callback_zero_pads_and_aborts_on_final_partial_frame(qtbot: QtBot):
    task = AudioTask(np.arange(6, dtype="float32"), fs=1000)
    task._is_first_chunk = False
    task._current_offset = 4
    outdata = np.full((4, 1), -1.0, dtype="float32")

    with pytest.raises(sd.CallbackAbort):
        task._audio_callback(outdata, 4, make_time_info(), sd.CallbackFlags())

    np.testing.assert_array_equal(outdata[:2, 0], [4, 5])
    np.testing.assert_array_equal(outdata[2:, 0], [0, 0])


def test_audio_callback_aborts_immediately_when_should_stop_set(qtbot: QtBot):
    task = AudioTask(np.arange(10, dtype="float32"), fs=1000)
    task._is_first_chunk = False
    task._should_stop = True
    outdata = np.full((4, 1), -1.0, dtype="float32")

    with pytest.raises(sd.CallbackAbort):
        task._audio_callback(outdata, 4, make_time_info(), sd.CallbackFlags())

    np.testing.assert_array_equal(outdata[:, 0], [-1.0, -1.0, -1.0, -1.0])


# --------------------------- _open_stream ---------------------------


def test_open_stream_returns_stream_on_first_successful_latency(
    monkeypatch: pytest.MonkeyPatch,
):
    calls = []
    fake_stream = object()

    def fake_output_stream(**kwargs: object) -> object:
        calls.append(kwargs["latency"])
        return fake_stream

    monkeypatch.setattr(audio_task_module.sd, "OutputStream", fake_output_stream)
    task = AudioTask(np.zeros(4), fs=1000)

    result = task._open_stream(1000, 1)

    assert result is fake_stream
    assert calls == ["low"]


def test_open_stream_falls_back_through_latencies_on_port_audio_error(
    monkeypatch: pytest.MonkeyPatch,
):
    calls = []
    fake_stream = object()

    def fake_output_stream(**kwargs: object) -> object:
        calls.append(kwargs["latency"])
        if kwargs["latency"] != "high":
            raise sd.PortAudioError("nope")
        return fake_stream

    monkeypatch.setattr(audio_task_module.sd, "OutputStream", fake_output_stream)
    task = AudioTask(np.zeros(4), fs=1000)

    result = task._open_stream(1000, 1)

    assert result is fake_stream
    assert calls == ["low", "high"]


def test_open_stream_raises_last_error_when_all_latencies_fail(
    monkeypatch: pytest.MonkeyPatch,
):
    def fake_output_stream(**kwargs: object) -> object:
        raise sd.PortAudioError(f"fail-{kwargs['latency']}")

    monkeypatch.setattr(audio_task_module.sd, "OutputStream", fake_output_stream)
    task = AudioTask(np.zeros(4), fs=1000)

    with pytest.raises(sd.PortAudioError, match="fail-None"):
        task._open_stream(1000, 1)


def test_open_stream_resets_is_first_chunk_flag(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(audio_task_module.sd, "OutputStream", lambda **kwargs: object())
    task = AudioTask(np.zeros(4), fs=1000)
    task._is_first_chunk = False

    task._open_stream(1000, 1)

    assert task._is_first_chunk is True


# --------------------------- stop ---------------------------


def test_stop_sets_should_stop_flag():
    task = AudioTask(np.zeros(4), fs=1000)
    assert task._should_stop is False

    task.stop()

    assert task._should_stop is True
