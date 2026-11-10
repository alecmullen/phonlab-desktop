from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
)
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)


def two_tier_repository() -> tuple[InMemAnnotationRepository, int]:
    """Tiers "word" and "phone" over nodes at 0, 1 and 2, two labels each"""
    repository = InMemAnnotationRepository()
    id = repository.create_annotation("sample")
    repository.create_nodes(id, [0.0, 1.0, 2.0], 0.005)
    repository.create_types(
        id,
        [
            AnnotationType(
                "word", [AnnotationLabel(0, 1, "a"), AnnotationLabel(1, 2, "b")]
            ),
            AnnotationType(
                "phone", [AnnotationLabel(0, 1, "p"), AnnotationLabel(1, 2, "q")]
            ),
        ],
    )
    return repository, id


def tier(annotation: Annotation, name: str) -> AnnotationType:
    return next(type for type in annotation.types if type.type == name)


def label_texts(annotation: Annotation, name: str) -> list[str]:
    return [label.label for label in tier(annotation, name).labels]


def test_label_ids_are_unique_across_tiers():
    repository, id = two_tier_repository()

    annotation = repository.get_annotation_by_id(id)

    ids = [label.id for type in annotation.types for label in type.labels]
    assert len(ids) == len(set(ids)) == 4


def test_create_label_assigns_id_unique_across_tiers():
    repository, id = two_tier_repository()
    annotation = repository.get_annotation_by_id(id)
    phone = tier(annotation, "phone")

    created = repository.create_label(AnnotationLabel(0, 2, "new"), phone.id)

    existing = {label.id for type in annotation.types for label in type.labels}
    assert created.id not in existing


def test_update_label_changes_only_the_label_in_its_own_tier():
    repository, id = two_tier_repository()
    annotation = repository.get_annotation_by_id(id)
    q = tier(annotation, "phone").labels[1]

    repository.update_label(AnnotationLabel(q.s_node, q.e_node, "Q", q.id))

    updated = repository.get_annotation_by_id(id)
    assert label_texts(updated, "phone") == ["p", "Q"]
    assert label_texts(updated, "word") == ["a", "b"]


def test_update_label_keeps_other_tier_label_nodes_intact():
    repository, id = two_tier_repository()
    annotation = repository.get_annotation_by_id(id)
    q = tier(annotation, "phone").labels[1]

    repository.update_label(AnnotationLabel(q.s_node, q.e_node, "Q", q.id))

    updated = repository.get_annotation_by_id(id)
    assert [(label.s_node, label.e_node) for label in tier(updated, "word").labels] == [
        (label.s_node, label.e_node) for label in tier(annotation, "word").labels
    ]


def test_delete_label_removes_only_the_label_in_its_own_tier():
    repository, id = two_tier_repository()
    annotation = repository.get_annotation_by_id(id)

    repository.delete_label(tier(annotation, "phone").labels[0])

    updated = repository.get_annotation_by_id(id)
    assert label_texts(updated, "phone") == ["q"]
    assert label_texts(updated, "word") == ["a", "b"]
