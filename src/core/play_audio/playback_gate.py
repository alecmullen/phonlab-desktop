import threading
from collections.abc import Iterator
from contextlib import contextmanager


class PlaybackGate:
    """Tells background work whether audio is playing, so heavy computations
    can wait for playback to end. Playback is glitchy while another thread
    holds Python's interpreter lock for tens of milliseconds at a time, as
    some of phonlab's formant trackers do. It is shared by every document,
    since any of them may be playing."""

    def __init__(self):
        self._condition = threading.Condition()
        self._playing = 0

    @contextmanager
    def playing(self) -> Iterator[None]:
        """Held while audio is playing"""
        with self._condition:
            self._playing += 1
        try:
            yield
        finally:
            with self._condition:
                self._playing -= 1
                self._condition.notify_all()

    def is_playing(self) -> bool:
        with self._condition:
            return self._playing > 0

    def wait_until_idle(self, timeout: float | None = None) -> bool:
        """Block until no audio is playing. False if `timeout` seconds went by
        first."""
        with self._condition:
            return self._condition.wait_for(lambda: self._playing == 0, timeout)


PLAYBACK_GATE = PlaybackGate()
