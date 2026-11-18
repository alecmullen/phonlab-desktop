from dataclasses import dataclass

from ui.base.state import State


@dataclass(frozen=True)
class ArrangeTiersAction(State):
    """Emitted by an annotation view when the user asks to show and order the tiers"""
