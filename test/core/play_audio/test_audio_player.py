from collections.abc import Iterator

import numpy as np
import pytest
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from pytestqt.qtbot import QtBot

import core.play_audio.audio_player as audio_player_module
from core.play_audio.audio_player import AudioPlayer
from core.play_audio.entity.latency_info import LatencyInfo


class FakeAudioWorker(QObject):
    started = pyqtSignal()
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, latency_slot: object):
        super().__init__()
        self.latency_slot = latency_slot
        self.play_calls: list[tuple[np.ndarray, int]] = []
        self.stop_calls = 0

    @pyqtSlot(object, int)
    def play(self, audio_data: np.ndarray, fs: int) -> None:
        self.play_calls.append((audio_data, fs))

    def stop(self) -> None:
        self.stop_calls += 1


@pytest.fixture
def player(monkeypatch: pytest.MonkeyPatch, qtbot: QtBot) -> Iterator[AudioPlayer]:
    monkeypatch.setattr(audio_player_module, "AudioWorker", FakeAudioWorker)
    audio_player = AudioPlayer()
    yield audio_player
    audio_player._audio_thread.quit()
    audio_player._audio_thread.wait(2000)


# --------------------------- _get_current_time ---------------------------


def test_get_current_time_returns_start_time_when_not_yet_audible(
    player: AudioPlayer,
):
    player._start_time = 5.0
    player._audible_start_time = None

    assert player._get_current_time() == 5.0


def test_get_current_time_computes_elapsed_since_audible_start(
    player: AudioPlayer, monkeypatch: pytest.MonkeyPatch
):
    player._start_time = 2.0
    player._audible_start_time = 100.0
    player._audio_length_time = 10.0
    monkeypatch.setattr(audio_player_module.time, "monotonic", lambda: 103.0)

    assert player._get_current_time() == pytest.approx(5.0)


def test_get_current_time_clamps_to_audio_length(
    player: AudioPlayer, monkeypatch: pytest.MonkeyPatch
):
    player._start_time = 0.0
    player._audible_start_time = 100.0
    player._audio_length_time = 2.0
    monkeypatch.setattr(audio_player_module.time, "monotonic", lambda: 110.0)

    assert player._get_current_time() == pytest.approx(2.0)


def test_get_current_time_does_not_go_negative(
    player: AudioPlayer, monkeypatch: pytest.MonkeyPatch
):
    player._start_time = 1.0
    player._audible_start_time = 100.0
    player._audio_length_time = 5.0
    monkeypatch.setattr(audio_player_module.time, "monotonic", lambda: 90.0)

    assert player._get_current_time() == pytest.approx(1.0)


# --------------------------- play ---------------------------


def test_play_stops_current_playback_first(
    player: AudioPlayer, monkeypatch: pytest.MonkeyPatch
):
    stop_calls = []
    monkeypatch.setattr(player, "stop", lambda: stop_calls.append(True))

    player.play(np.zeros(10), 1000, start_time=1.0)

    assert stop_calls == [True]


def test_play_resets_state_and_emits_audio_queue(player: AudioPlayer):
    received = []
    player.audio_queue.connect(lambda data, fs: received.append((data, fs)))

    player.play(np.arange(2000, dtype=np.float64), 1000, start_time=3.0)

    assert player._start_time == 3.0
    assert player._audible_start_time is None
    assert player._audio_length_time == pytest.approx(2.0)
    assert len(received) == 1
    np.testing.assert_array_equal(received[0][0], np.arange(2000, dtype=np.float64))
    assert received[0][1] == 1000


# --------------------------- polling ---------------------------


def test_poll_playback_emits_current_playback_state(player: AudioPlayer):
    player._start_time = 1.0
    player._latency = 0.02
    received = []
    player.playback_poll.connect(received.append)

    player._poll_playback()

    assert len(received) == 1
    assert received[0].current_time == pytest.approx(1.0)
    assert received[0].latency == 0.02
    assert received[0].is_playing is True


def test_on_audio_started_starts_poll_timer(player: AudioPlayer):
    assert player.poll_timer.isActive() is False

    player._on_audio_started()

    assert player.poll_timer.isActive() is True


def test_on_audio_finished_emits_zero_poll_and_stops_timer(player: AudioPlayer):
    player._latency = 0.05
    player.poll_timer.start()
    received = []
    player.playback_poll.connect(received.append)

    player._on_audio_finished()

    assert received[-1].current_time == 0.0
    assert received[-1].latency == 0.05
    assert received[-1].is_playing is False
    assert player.poll_timer.isActive() is False


def test_on_latency_updates_latency_and_audible_start_time(player: AudioPlayer):
    player._on_latency(LatencyInfo(latency=0.03, audible_start_time=42.0))

    assert player._latency == 0.03
    assert player._audible_start_time == 42.0


def test_on_error_emits_playback_error_and_stops_timer(player: AudioPlayer):
    player.poll_timer.start()
    received = []
    player.playback_error.connect(received.append)

    player._on_error("boom")

    assert received == ["boom"]
    assert player.poll_timer.isActive() is False


# --------------------------- stop ---------------------------


def test_stop_stops_worker_and_timer(player: AudioPlayer):
    player.poll_timer.start()

    player.stop()

    assert player._audio_worker.stop_calls == 1
    assert player.poll_timer.isActive() is False
