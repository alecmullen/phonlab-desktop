from support.tier_labels import populate_project

from core.annotation.entity.tier_label import MatchMode
from core.annotation.replace_in_tier import ReplaceInTier
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from core.annotation.search_tier import SearchTier
from core.annotation.update_label import UpdateLabel


def make_use_cases() -> tuple[SearchTier, ReplaceInTier, InMemAnnotationRepository]:
    repository = InMemAnnotationRepository()
    populate_project(repository)
    return (
        SearchTier(repository),
        ReplaceInTier(UpdateLabel(repository)),
        repository,
    )


def texts(repository: InMemAnnotationRepository, stem: str, tier: str) -> list[str]:
    annotation = repository.find_annotation_by_file_stem(stem)
    assert annotation is not None
    return [
        label.label
        for type in annotation.types
        if type.type == tier
        for label in type.labels
    ]


def test_substring_replacement_is_stored():
    search, replace, repository = make_use_cases()
    hits = search("word", "cat", MatchMode.SUBSTRING)

    replace(hits, "cat", "dog", MatchMode.SUBSTRING)

    assert texts(repository, "a", "word") == ["dog", "dog", "dogs"]
    assert texts(repository, "b", "word") == ["bird", "dog"]


def test_exact_replacement_only_touches_whole_labels():
    search, replace, repository = make_use_cases()
    hits = search("word", "cat", MatchMode.EXACT)

    replace(hits, "cat", "feline", MatchMode.EXACT)

    assert texts(repository, "a", "word") == ["feline", "dog", "cats"]


def test_returns_labels_with_new_text():
    search, replace, _ = make_use_cases()
    hits = search("word", "cat", MatchMode.EXACT, "b")

    updated = replace(hits, "cat", "feline", MatchMode.EXACT)

    assert [hit.label.label for hit in updated] == ["feline"]
    assert updated[0].label.id == hits[0].label.id


def test_other_tiers_and_files_are_untouched():
    search, replace, repository = make_use_cases()

    replace(search("word", "dog", MatchMode.EXACT, "a"), "dog", "x", MatchMode.EXACT)

    assert texts(repository, "sub/c", "word") == ["dog"]
    assert texts(repository, "a", "phone") == ["k", "ae"]
