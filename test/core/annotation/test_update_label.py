from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
)
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from core.annotation.update_label import UpdateLabel
from core.annotation.update_node import UpdateNode


def seeded_repository() -> tuple[InMemAnnotationRepository, Annotation]:
    repository = InMemAnnotationRepository()
    annotation = repository.seed(
        Annotation(
            nodes={0: 0.0, 1: 1.0},
            types=[AnnotationType("word", [AnnotationLabel(0, 1, "a", id=0)])],
        )
    )
    return repository, annotation


def test_update_label_changes_label_text_in_repository():
    repository, annotation = seeded_repository()

    UpdateLabel(repository)(AnnotationLabel(0, 1, "changed", id=0))

    stored = repository.get_annotation_by_id(annotation.get_id())
    assert stored.types[0].labels == [AnnotationLabel(0, 1, "changed", id=0)]


def test_update_node_changes_node_time_in_repository():
    repository, annotation = seeded_repository()

    UpdateNode(repository)(1, 1.5)

    stored = repository.get_annotation_by_id(annotation.get_id())
    assert stored.nodes == {0: 0.0, 1: 1.5}
