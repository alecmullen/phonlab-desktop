import pytest

from core.annotation.entity.annotation import AnnotationLabel
from core.annotation.entity.tier_label import (
    MatchMode,
    TierLabel,
    label_matches,
    replace_in_label,
)


@pytest.mark.parametrize(
    ("text", "query", "mode", "expected"),
    [
        ("cat", "cat", MatchMode.EXACT, True),
        ("cats", "cat", MatchMode.EXACT, False),
        ("cats", "cat", MatchMode.SUBSTRING, True),
        ("cats", "dog", MatchMode.SUBSTRING, False),
        ("Cat", "cat", MatchMode.SUBSTRING, False),
        ("cat", "", MatchMode.SUBSTRING, False),
        ("", "", MatchMode.EXACT, False),
    ],
)
def test_label_matches(text: str, query: str, mode: MatchMode, expected: bool):
    assert label_matches(text, query, mode) is expected


def test_replace_in_label_exact_swaps_whole_label():
    assert replace_in_label("cat", "cat", "dog", MatchMode.EXACT) == "dog"


def test_replace_in_label_exact_ignores_longer_labels():
    assert replace_in_label("cats", "cat", "dog", MatchMode.EXACT) == "cats"


def test_replace_in_label_substring_swaps_every_occurrence():
    assert replace_in_label("catcat!", "cat", "d", MatchMode.SUBSTRING) == "dd!"


def test_replace_in_label_substring_can_delete():
    assert replace_in_label("cats", "s", "", MatchMode.SUBSTRING) == "cat"


def test_replace_in_label_leaves_non_matching_text():
    assert replace_in_label("bird", "cat", "dog", MatchMode.SUBSTRING) == "bird"


def test_sort_key_orders_by_file_then_time():
    def at(stem: str, start: float) -> TierLabel:
        return TierLabel(stem, "word", AnnotationLabel(0, 1, "x", 5), start, start + 1)

    labels = [at("b", 0.0), at("a", 2.0), at("a", 1.0)]

    assert [(l.file_stem, l.start) for l in sorted(labels, key=TierLabel.sort_key)] == [
        ("a", 1.0),
        ("a", 2.0),
        ("b", 0.0),
    ]
