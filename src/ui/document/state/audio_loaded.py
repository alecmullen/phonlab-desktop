from dataclasses import dataclass

from ui.base.state import State


@dataclass(frozen=True)
class AudioLoaded(State):
    is_loaded: bool = False
    fs: int = 0
