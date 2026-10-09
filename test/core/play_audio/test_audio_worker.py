from typing import ClassVar

import numpy as np
import pytest
import sounddevice as sd
from PyQt6.QtCore import QObject, pyqtSignal
from pytestqt.qtbot import QtBot

import core.play_audio.audio_worker as audio_worker_module
from core.play_audio.audio_worker import AudioWorker
from core.play_audio.entity.latency_info import LatencyInfo


class FakeAudioTask(QObject):
    latency = pyqtSignal(object)
    instances: ClassVar[list["FakeAudioTask"]] = []

    def __init__(self, audio_data: np.ndarray, fs: int):
        super().__init__()
        self.audio_data = audio_data
        self.fs = fs
        self.called = False
        self.stop_called = False
        FakeAudioTask.instances.append(self)

    def __call__(self) -> None:
        self.called = True

    def stop(self) -> None:
        self.stop_called = True


@pytest.fixture
def fake_audio_task(monkeypatch: pytest.MonkeyPatch) -> type[FakeAudioTask]:
    FakeAudioTask.instances = []
    monkeypatch.setattr(audio_worker_module, "AudioTask", FakeAudioTask)
    return FakeAudioTask


def test_play_emits_started_creates_and_runs_task(
    qtbot: QtBot, fake_audio_task: type[FakeAudioTask]
):
    latency_received = []
    worker = AudioWorker(latency_received.append)
    started_received = []
    worker.started.connect(lambda: started_received.append(True))

    worker.play(np.zeros(4), 1000)

    assert started_received == [True]
    assert len(fake_audio_task.instances) == 1
    task = fake_audio_task.instances[0]
    assert task.called is True

    task.latency.emit(LatencyInfo(0.01, 123.0))
    assert latency_received == [LatencyInfo(0.01, 123.0)]


def test_play_emits_finished_after_successful_playback(
    qtbot: QtBot, fake_audio_task: type[FakeAudioTask]
):
    worker = AudioWorker(lambda info: None)
    finished_received = []
    worker.finished.connect(lambda: finished_received.append(True))

    worker.play(np.zeros(4), 1000)

    assert finished_received == [True]


def test_play_creates_a_new_task_on_each_call(
    qtbot: QtBot, fake_audio_task: type[FakeAudioTask]
):
    worker = AudioWorker(lambda info: None)

    worker.play(np.zeros(2), 1000)
    first_task = worker._task
    worker.play(np.zeros(2), 1000)

    assert len(fake_audio_task.instances) == 2
    assert worker._task is not first_task


def test_play_catches_port_audio_error_emits_error_and_still_emits_finished(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    class FailingTask(QObject):
        latency = pyqtSignal(object)

        def __init__(self, audio_data: np.ndarray, fs: int):
            super().__init__()

        def __call__(self) -> None:
            raise sd.PortAudioError("boom")

        def stop(self) -> None:
            pass

    monkeypatch.setattr(audio_worker_module, "AudioTask", FailingTask)
    worker = AudioWorker(lambda info: None)
    errors = []
    finished = []
    worker.error.connect(errors.append)
    worker.finished.connect(lambda: finished.append(True))

    worker.play(np.zeros(2), 1000)

    assert len(errors) == 1
    assert "boom" in errors[0]
    assert finished == [True]


def test_play_reraises_other_exceptions_and_skips_finished(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    class FailingTask(QObject):
        latency = pyqtSignal(object)

        def __init__(self, audio_data: np.ndarray, fs: int):
            super().__init__()

        def __call__(self) -> None:
            raise ValueError("kaboom")

        def stop(self) -> None:
            pass

    monkeypatch.setattr(audio_worker_module, "AudioTask", FailingTask)
    worker = AudioWorker(lambda info: None)
    errors = []
    finished = []
    worker.error.connect(errors.append)
    worker.finished.connect(lambda: finished.append(True))

    with pytest.raises(ValueError, match="kaboom"):
        worker.play(np.zeros(2), 1000)

    assert len(errors) == 1
    assert "kaboom" in errors[0]
    assert finished == []


def test_stop_forwards_to_task_when_task_exists(
    qtbot: QtBot, fake_audio_task: type[FakeAudioTask]
):
    worker = AudioWorker(lambda info: None)
    worker.play(np.zeros(2), 1000)

    worker.stop()

    assert fake_audio_task.instances[0].stop_called is True


def test_stop_is_a_noop_when_no_task(qtbot: QtBot):
    worker = AudioWorker(lambda info: None)

    worker.stop()
