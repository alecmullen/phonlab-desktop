import pytest

from core.annotation.add_tiers import (
    AddTiers,
    DuplicateTierNameError,
    EmptyTierNameError,
    NoTiersError,
)
from core.annotation.entity.annotation import AnnotationType
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)


def make_use_case() -> tuple[AddTiers, InMemAnnotationRepository]:
    repository = InMemAnnotationRepository()
    return AddTiers(repository), repository


def test_adds_tiers_to_a_file_that_has_no_annotation_yet():
    add_tiers, repository = make_use_case()

    annotation = add_tiers("sample", ["word", "break"])

    assert [(t.type, t.labels) for t in annotation.types] == [
        ("word", []),
        ("break", []),
    ]
    assert annotation.nodes == {}
    assert repository.find_annotation_by_file_stem("sample") == annotation


def test_adds_tiers_to_a_file_registered_without_annotation():
    add_tiers, repository = make_use_case()
    registered = repository.create_annotation("sample")

    annotation = add_tiers("sample", ["word"])

    assert annotation.id == registered
    assert len(repository.filenames) == 1


def test_adds_a_tier_to_an_existing_annotation_keeping_what_it_has():
    add_tiers, repository = make_use_case()
    id = repository.create_annotation("sample")
    repository.create_nodes(id, [0.0, 1.0], 0.005)
    repository.create_types(id, [AnnotationType("word", [])])
    before = repository.get_annotation_by_id(id)

    annotation = add_tiers("sample", ["phone"])

    assert [t.type for t in annotation.types] == ["word", "phone"]
    assert annotation.nodes == before.nodes
    assert annotation.types[0] == before.types[0]


def test_new_tiers_get_ids_of_their_own():
    add_tiers, _ = make_use_case()

    annotation = add_tiers("sample", ["a", "b"])

    assert len({t.get_id() for t in annotation.types}) == 2


def test_tier_names_are_trimmed():
    add_tiers, _ = make_use_case()

    assert add_tiers("sample", ["  word  "]).types[0].type == "word"


def test_no_tiers_is_an_error():
    add_tiers, repository = make_use_case()

    with pytest.raises(NoTiersError):
        add_tiers("sample", [])

    assert repository.filenames == {}


@pytest.mark.parametrize("name", ["", "   "])
def test_a_blank_name_is_an_error_and_changes_nothing(name: str):
    add_tiers, repository = make_use_case()

    with pytest.raises(EmptyTierNameError):
        add_tiers("sample", ["word", name])

    assert repository.filenames == {}  # the good tier was not added either


def test_a_name_the_file_already_has_is_an_error():
    add_tiers, repository = make_use_case()
    add_tiers("sample", ["word"])

    with pytest.raises(DuplicateTierNameError) as error:
        add_tiers("sample", ["phone", " word"])

    assert error.value.name == "word"
    annotation = repository.find_annotation_by_file_stem("sample")
    assert annotation is not None
    assert [t.type for t in annotation.types] == ["word"]


def test_the_same_name_twice_in_one_request_is_an_error():
    add_tiers, _ = make_use_case()

    with pytest.raises(DuplicateTierNameError):
        add_tiers("sample", ["word", "word"])


def test_tier_names_are_case_sensitive():
    add_tiers, _ = make_use_case()

    annotation = add_tiers("sample", ["Word", "word"])

    assert [t.type for t in annotation.types] == ["Word", "word"]


def test_the_same_name_can_be_used_in_another_file():
    add_tiers, _ = make_use_case()
    add_tiers("one", ["word"])

    assert [t.type for t in add_tiers("two", ["word"]).types] == ["word"]
