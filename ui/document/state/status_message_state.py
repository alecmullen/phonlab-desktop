from dataclasses import dataclass


@dataclass
class StatusMessageState:
    message: str = ""