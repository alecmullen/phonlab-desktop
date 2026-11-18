from core.annotation.entity.annotation import AnnotationType
from core.annotation.list_tier_names import ListTierNames
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)


def test_lists_the_tier_names_used_in_the_database():
    repository = InMemAnnotationRepository()
    id = repository.create_annotation("sample")
    repository.create_types(id, [AnnotationType("word", [])])

    assert ListTierNames(repository)() == ["word"]


def test_lists_nothing_for_an_empty_database():
    assert ListTierNames(InMemAnnotationRepository())() == []
