from dataclasses import dataclass, field

from ui.base.state import State


@dataclass(frozen=True)
class AddTiersAction(State):
    """Ask the user which tiers to add: `available` are the tier names used in the
    project database, `existing` the ones this document already has"""

    available: list[str] = field(default_factory=list)
    existing: list[str] = field(default_factory=list)
