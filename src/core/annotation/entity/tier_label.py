from dataclasses import dataclass
from enum import StrEnum

from core.annotation.entity.annotation import AnnotationLabel


class MatchMode(StrEnum):
    EXACT = "exact"
    SUBSTRING = "substring"


@dataclass(frozen=True)
class TierLabel:
    """A label together with where it lives: which file and tier it belongs to and
    the times of its start and end nodes"""

    file_stem: str
    tier_name: str
    label: AnnotationLabel
    start: float
    end: float

    def sort_key(self) -> tuple[str, float, float, int]:
        return (self.file_stem, self.start, self.end, self.label.id or 0)


def label_matches(text: str, query: str, mode: MatchMode) -> bool:
    """An empty query matches nothing"""
    if query == "":
        return False
    if mode == MatchMode.EXACT:
        return text == query
    return query in text


def replace_in_label(text: str, query: str, replacement: str, mode: MatchMode) -> str:
    """Exact mode swaps the whole label for the replacement; substring mode swaps
    every occurrence of the query within the label"""
    if not label_matches(text, query, mode):
        return text
    if mode == MatchMode.EXACT:
        return replacement
    return text.replace(query, replacement)
