from core.annotation.entity.tier_label import MatchMode, TierLabel
from core.annotation.replace_in_tier import ReplaceInTier
from core.annotation.search_tier import SearchTier
from ui.annotation.state.tier_search_state import (
    TierLabelsChangedState,
    TierSearchMatchState,
    TierSearchState,
)
from ui.base.view_model import ViewModel


class TierSearchViewModel(ViewModel):
    """Finds, and optionally replaces, label text on one tier, in one file or in every
    file of the project. The search moves forward from the last match it showed"""

    def __init__(
        self,
        search_tier: SearchTier,
        replace_in_tier: ReplaceInTier,
        is_project: bool = False,
    ):
        super().__init__()
        self.search_tier_use_case = search_tier
        self.replace_in_tier_use_case = replace_in_tier
        self.is_project = is_project

        self.tier_name = ""
        self.file_stem = ""
        # Where the search resumes: matches sorting after this are "next"
        self.cursor: tuple[str, float, float, int] = ("", 0.0, 0.0, 0)

    def set_target(self, tier_name: str, file_stem: str, start: float = 0.0):
        """Search `tier_name` as found in `file_stem`, beginning at time `start`"""
        self.tier_name = tier_name
        self.file_stem = file_stem
        self.cursor = (file_stem, start, -1.0, -1)
        self.state_changed.emit(
            TierSearchState(tier_name, can_search_project=self.is_project)
        )

    def find_next(self, query: str, exact: bool, whole_project: bool):
        matches = self._search(query, exact, whole_project)
        if len(matches) == 0:
            self._emit_message(self.tr("No matches"))
            return

        after = [match for match in matches if match.sort_key() > self.cursor]
        wrapped = len(after) == 0
        match = matches[0] if wrapped else after[0]
        self.cursor = match.sort_key()

        position = matches.index(match) + 1
        message = self.tr("Match {} of {}").format(position, len(matches))
        if wrapped:
            message = self.tr("{} (wrapped around)").format(message)
        self._emit_message(message)
        self.state_changed.emit(
            TierSearchMatchState(match.file_stem, match.start, match.end)
        )

    def replace(self, query: str, replacement: str, exact: bool, whole_project: bool):
        """Replaces the match the search is resting on, then moves to the next one. When
        the search is not resting on a match, just finds the next one"""
        current = [
            match
            for match in self._search(query, exact, whole_project)
            if match.sort_key() == self.cursor
        ]
        if len(current) > 0:
            self._replace(current, query, replacement, exact)
        self.find_next(query, exact, whole_project)

    def replace_all(
        self, query: str, replacement: str, exact: bool, whole_project: bool
    ):
        matches = self._search(query, exact, whole_project)
        if len(matches) == 0:
            self._emit_message(self.tr("No matches"))
            return

        self._replace(matches, query, replacement, exact)
        self._emit_message(self.tr("Replaced {} labels").format(len(matches)))

    def _search(self, query: str, exact: bool, whole_project: bool) -> list[TierLabel]:
        return self.search_tier_use_case(
            self.tier_name,
            query,
            _mode(exact),
            None if whole_project else self.file_stem,
        )

    def _replace(
        self, matches: list[TierLabel], query: str, replacement: str, exact: bool
    ):
        self.replace_in_tier_use_case(matches, query, replacement, _mode(exact))
        self.state_changed.emit(
            TierLabelsChangedState(frozenset(match.file_stem for match in matches))
        )

    def _emit_message(self, message: str):
        self.state_changed.emit(
            TierSearchState(self.tier_name, self.is_project, message)
        )


def _mode(exact: bool) -> MatchMode:
    return MatchMode.EXACT if exact else MatchMode.SUBSTRING
