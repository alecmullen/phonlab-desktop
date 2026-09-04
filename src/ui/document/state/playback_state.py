from dataclasses import dataclass

from ui.base.state import State


@dataclass
class PlaybackState(State):
    is_playing: bool = False
    position: float = 0.0
    high_latency: bool = False
