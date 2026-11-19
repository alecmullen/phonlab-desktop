from support.tier_labels import populate_project

from core.annotation.replace_in_tier import ReplaceInTier
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from core.annotation.search_tier import SearchTier
from core.annotation.update_label import UpdateLabel
from ui.annotation.state.tier_search_state import (
    TierLabelsChangedState,
    TierSearchMatchState,
    TierSearchState,
)
from ui.annotation.tier_search_view_model import TierSearchViewModel
from ui.base.state import State


def make_view_model(
    is_project: bool = True,
) -> tuple[TierSearchViewModel, InMemAnnotationRepository, list[State]]:
    repository = InMemAnnotationRepository()
    populate_project(repository)
    view_model = TierSearchViewModel(
        SearchTier(repository),
        ReplaceInTier(UpdateLabel(repository)),
        is_project,
    )
    states: list[State] = []
    view_model.subscribe(states.append)
    return view_model, repository, states


def matches(states: list[State]) -> list[tuple[str, float]]:
    return [
        (s.file_stem, s.start) for s in states if isinstance(s, TierSearchMatchState)
    ]


def last_message(states: list[State]) -> str:
    return [s for s in states if isinstance(s, TierSearchState)][-1].message


def texts(repository: InMemAnnotationRepository, stem: str) -> list[str]:
    annotation = repository.find_annotation_by_file_stem(stem)
    assert annotation is not None
    return [l.label for t in annotation.types if t.type == "word" for l in t.labels]


def test_set_target_reports_tier_and_whether_project_search_is_possible():
    view_model, _, states = make_view_model(is_project=False)

    view_model.set_target("word", "a")

    assert states == [TierSearchState("word", can_search_project=False)]


def test_find_next_steps_through_matches_in_file_and_wraps():
    view_model, _, states = make_view_model()
    view_model.set_target("word", "a")

    for _ in range(3):
        view_model.find_next("cat", exact=False, whole_project=False)

    assert matches(states) == [("a", 0.0), ("a", 2.0), ("a", 0.0)]
    assert last_message(states) == "Match 1 of 2 (wrapped around)"


def test_find_next_reports_position_among_matches():
    view_model, _, states = make_view_model()
    view_model.set_target("word", "a")

    view_model.find_next("cat", exact=False, whole_project=False)

    assert last_message(states) == "Match 1 of 2"


def test_find_next_exact_skips_longer_labels():
    view_model, _, states = make_view_model()
    view_model.set_target("word", "a")

    view_model.find_next("cat", exact=True, whole_project=False)
    view_model.find_next("cat", exact=True, whole_project=False)

    assert matches(states) == [("a", 0.0), ("a", 0.0)]


def test_find_next_in_project_moves_on_to_other_files():
    view_model, _, states = make_view_model()
    view_model.set_target("word", "a")

    for _ in range(4):
        view_model.find_next("cat", exact=False, whole_project=True)

    assert matches(states) == [("a", 0.0), ("a", 2.0), ("b", 1.0), ("a", 0.0)]


def test_find_next_starts_at_given_time():
    view_model, _, states = make_view_model()
    view_model.set_target("word", "a", start=1.5)

    view_model.find_next("cat", exact=False, whole_project=False)

    assert matches(states) == [("a", 2.0)]


def test_find_next_with_no_matches_says_so_and_does_not_navigate():
    view_model, _, states = make_view_model()
    view_model.set_target("word", "a")

    view_model.find_next("zebra", exact=False, whole_project=True)

    assert matches(states) == []
    assert last_message(states) == "No matches"


def test_replace_rewrites_current_match_and_moves_to_next():
    view_model, repository, states = make_view_model()
    view_model.set_target("word", "a")
    view_model.find_next("cat", exact=False, whole_project=False)

    view_model.replace("cat", "dog", exact=False, whole_project=False)

    assert texts(repository, "a") == ["dog", "dog", "cats"]
    assert TierLabelsChangedState(frozenset({"a"})) in states
    assert matches(states)[-1] == ("a", 2.0)


def test_replace_without_current_match_only_finds_next():
    view_model, repository, states = make_view_model()
    view_model.set_target("word", "a")

    view_model.replace("cat", "dog", exact=False, whole_project=False)

    assert texts(repository, "a") == ["cat", "dog", "cats"]
    assert matches(states) == [("a", 0.0)]
    assert not any(isinstance(s, TierLabelsChangedState) for s in states)


def test_replace_leaves_current_label_alone_when_it_does_not_match_query():
    view_model, repository, _ = make_view_model()
    view_model.set_target("word", "a")
    view_model.find_next("cat", exact=False, whole_project=False)

    view_model.replace("dog", "x", exact=False, whole_project=False)

    assert texts(repository, "a") == ["cat", "dog", "cats"]


def test_replace_all_rewrites_every_match_in_scope():
    view_model, repository, states = make_view_model()
    view_model.set_target("word", "a")

    view_model.replace_all("cat", "dog", exact=False, whole_project=True)

    assert texts(repository, "a") == ["dog", "dog", "dogs"]
    assert texts(repository, "b") == ["bird", "dog"]
    assert TierLabelsChangedState(frozenset({"a", "b"})) in states
    assert last_message(states) == "Replaced 3 labels"


def test_replace_all_in_file_leaves_other_files_alone():
    view_model, repository, _ = make_view_model()
    view_model.set_target("word", "a")

    view_model.replace_all("cat", "dog", exact=True, whole_project=False)

    assert texts(repository, "a") == ["dog", "dog", "cats"]
    assert texts(repository, "b") == ["bird", "cat"]


def test_replace_all_with_no_matches_changes_nothing():
    view_model, _, states = make_view_model()
    view_model.set_target("word", "a")

    view_model.replace_all("zebra", "x", exact=False, whole_project=True)

    assert last_message(states) == "No matches"
    assert not any(isinstance(s, TierLabelsChangedState) for s in states)
