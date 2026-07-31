from dataclasses import dataclass


@dataclass
class DocumentWindowState:
    start: int = 0
    end: int = 0
    max_start: int = 0
