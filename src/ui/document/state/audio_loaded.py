from dataclasses import dataclass


@dataclass(frozen=True)
class AudioLoaded:
    fs: int = 0
