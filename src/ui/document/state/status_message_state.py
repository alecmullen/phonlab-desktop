from dataclasses import dataclass

from ui.base.state import State


@dataclass
class StatusMessageState(State):
    message: str = ""
