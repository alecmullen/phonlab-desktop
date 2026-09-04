from dataclasses import dataclass

from ui.base.state import State


@dataclass(frozen=True)
class AudioLoaded(State):
    fs: int = 0
