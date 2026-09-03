from dataclasses import dataclass


@dataclass
class MarkState:
    position: float = 0.0  # seconds
    is_set: bool = False
