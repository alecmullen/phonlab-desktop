from dataclasses import dataclass, field

from ui.base.state import State


@dataclass(frozen=True)
class TierSearchAction(State):
    """Emitted by an annotation view when the user asks to search a tier. `start` is
    the time (s) at the left of the view, where the search begins"""

    tier_name: str
    file_stem: str
    start: float = 0.0


@dataclass(frozen=True)
class TierSearchState(State):
    """What the search dialog shows: the tier being searched and the outcome of the
    last search or replacement"""

    tier_name: str = ""
    can_search_project: bool = False
    message: str = ""


@dataclass(frozen=True)
class TierSearchMatchState(State):
    """The label to show the user: which file, and the span (s) it covers"""

    file_stem: str
    start: float
    end: float


@dataclass(frozen=True)
class TierLabelsChangedState(State):
    """Files whose labels were rewritten behind the back of any document showing them"""

    file_stems: frozenset[str] = field(default_factory=frozenset)
