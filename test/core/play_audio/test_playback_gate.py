import threading

import pytest

from core.play_audio.playback_gate import PlaybackGate


def test_the_gate_is_idle_until_audio_plays():
    gate = PlaybackGate()
    assert not gate.is_playing()

    with gate.playing():
        assert gate.is_playing()

    assert not gate.is_playing()


def test_overlapping_playbacks_hold_the_gate_until_the_last_ends():
    gate = PlaybackGate()  # (several documents can play at once)

    with gate.playing():
        with gate.playing():
            pass
        assert gate.is_playing()

    assert not gate.is_playing()


def test_the_gate_opens_again_when_playback_fails():
    gate = PlaybackGate()

    with pytest.raises(RuntimeError), gate.playing():
        raise RuntimeError("audio device lost")

    assert not gate.is_playing()


def test_waiting_while_idle_returns_at_once():
    assert PlaybackGate().wait_until_idle(timeout=5) is True


def test_waiting_gives_up_after_the_timeout_while_audio_plays():
    gate = PlaybackGate()

    with gate.playing():
        assert gate.wait_until_idle(timeout=0.05) is False


def test_waiting_ends_when_playback_ends():
    gate = PlaybackGate()
    released = threading.Event()
    result = []

    def wait():
        result.append(gate.wait_until_idle(timeout=5))
        released.set()

    with gate.playing():
        thread = threading.Thread(target=wait)
        thread.start()
        assert not released.wait(0.1)  # still waiting

    assert released.wait(5)
    thread.join()
    assert result == [True]
