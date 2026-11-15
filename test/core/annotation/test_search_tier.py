from support.tier_labels import populate_project

from core.annotation.entity.tier_label import MatchMode, TierLabel
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from core.annotation.search_tier import SearchTier


def make_search() -> SearchTier:
    repository = InMemAnnotationRepository()
    populate_project(repository)
    return SearchTier(repository)


def found(hits: list[TierLabel]) -> list[tuple[str, str, float]]:
    return [(hit.file_stem, hit.label.label, hit.start) for hit in hits]


def test_exact_match_finds_whole_labels_across_project():
    hits = make_search()("word", "cat", MatchMode.EXACT)

    assert found(hits) == [("a", "cat", 0.0), ("b", "cat", 1.0)]


def test_substring_match_includes_longer_labels():
    hits = make_search()("word", "cat", MatchMode.SUBSTRING)

    assert found(hits) == [("a", "cat", 0.0), ("a", "cats", 2.0), ("b", "cat", 1.0)]


def test_file_stem_limits_search_to_one_file():
    hits = make_search()("word", "cat", MatchMode.SUBSTRING, "b")

    assert found(hits) == [("b", "cat", 1.0)]


def test_only_searches_tier_with_that_name():
    hits = make_search()("phone", "a", MatchMode.SUBSTRING)

    assert found(hits) == [("a", "ae", 1.0)]


def test_results_carry_label_ids_and_end_times():
    hit = make_search()("word", "dog", MatchMode.EXACT, "sub/c")[0]

    assert hit.label.id is not None
    assert (hit.start, hit.end) == (0.0, 1.0)


def test_empty_query_matches_nothing():
    assert make_search()("word", "", MatchMode.SUBSTRING) == []


def test_unknown_tier_matches_nothing():
    assert make_search()("nope", "cat", MatchMode.SUBSTRING) == []
