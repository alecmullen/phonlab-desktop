import pytest
from support.view_models import make_create_label

from core.annotation.create_label import ZeroLengthLabelError
from core.annotation.delete_node import DeleteNode
from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
)
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from res.constants import SAME_NODE_THRESHOLD


def make_annotation(
    nodes: dict[int, float], tiers: list[list[tuple[int, int, str]]]
) -> Annotation:
    return Annotation(
        nodes=nodes,
        types=[
            AnnotationType(
                f"tier{idx}",
                [AnnotationLabel(*label, id=id) for id, label in enumerate(labels)],
            )
            for idx, labels in enumerate(tiers)
        ],
    )


def create_label(
    annotation: Annotation,
    type_id: int,
    start: float,
    end: float,
    same_node_threshold: float = SAME_NODE_THRESHOLD,
) -> Annotation:
    repository = InMemAnnotationRepository()
    seeded = repository.seed(annotation)
    return make_create_label(repository)(
        seeded, type_id, start, end, same_node_threshold
    )


def label_times(annotation: Annotation, tier: int) -> list[tuple]:
    nodes = annotation.nodes
    return sorted(
        (nodes[label.s_node], nodes[label.e_node], label.label)
        for label in annotation.types[tier].labels
    )


def test_create_label_on_empty_tier_creates_nodes_and_label():
    annotation = make_annotation({0: 0.0, 1: 3.0}, [[]])

    result = create_label(annotation, 0, 1.0, 2.0)

    assert result.nodes == {0: 0.0, 1: 3.0, 2: 1.0, 3: 2.0}
    assert result.types[0].labels == [AnnotationLabel(2, 3, id=0)]


def test_create_label_reuses_nodes_within_threshold():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a")]])

    result = create_label(
        annotation, 0, 1.0 + SAME_NODE_THRESHOLD / 2, 2.0 - SAME_NODE_THRESHOLD / 2
    )

    assert result.nodes == {0: 0.0, 1: 1.0, 2: 2.0}
    assert label_times(result, 0) == [(0.0, 1.0, "a"), (1.0, 2.0, "")]


def test_create_label_assigns_id_to_new_label():
    annotation = Annotation(
        nodes={0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0},
        types=[AnnotationType("word", [AnnotationLabel(0, 1, "a", id=5)])],
    )

    result = create_label(annotation, 0, 2.0, 3.0)

    assert [label.id for label in result.types[0].labels] == [5, 6]


def test_create_label_replaces_labels_inside_selection():
    annotation = make_annotation(
        {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0}, [[(0, 1, "a"), (1, 2, "b"), (2, 3, "c")]]
    )

    result = create_label(annotation, 0, 0.5, 2.5)

    assert label_times(result, 0) == [
        (0.0, 0.5, "a"),
        (0.5, 2.5, ""),
        (2.5, 3.0, "c"),
    ]


def test_create_label_inside_existing_label_splits_it():
    annotation = make_annotation({0: 0.0, 1: 3.0}, [[(0, 1, "a")]])

    result = create_label(annotation, 0, 1.0, 2.0)

    assert label_times(result, 0) == [
        (0.0, 1.0, "a"),
        (1.0, 2.0, ""),
        (2.0, 3.0, ""),
    ]


def test_create_label_only_changes_target_tier():
    annotation = make_annotation(
        {0: 0.0, 1: 3.0}, [[(0, 1, "a")], [(0, 1, "b")], [(0, 1, "c")]]
    )

    result = create_label(annotation, 1, 1.0, 2.0)

    assert result.types[0].labels == annotation.types[0].labels
    assert result.types[2].labels == annotation.types[2].labels
    assert label_times(result, 1) == [
        (0.0, 1.0, "b"),
        (1.0, 2.0, ""),
        (2.0, 3.0, ""),
    ]


def test_create_label_splitting_label_gives_every_label_an_id():
    annotation = make_annotation({0: 0.0, 1: 3.0}, [[(0, 1, "a")]])

    result = create_label(annotation, 0, 1.0, 2.0)

    ids = [label.id for label in result.types[0].labels]
    assert None not in ids
    assert len(set(ids)) == 3


def test_delete_node_after_splitting_label_merges_with_new_label():
    annotation = make_annotation({0: 0.0, 1: 3.0}, [[(0, 1, "a")]])
    annotation = create_label(annotation, 0, 1.0, 2.0)

    repository = InMemAnnotationRepository()
    result = DeleteNode(repository)(repository.seed(annotation), 2)

    assert label_times(result, 0) == [(0.0, 2.0, "a"), (2.0, 3.0, "")]


def test_create_label_custom_threshold_snaps_both_ends_to_existing_nodes():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0}, [[]])

    result = create_label(annotation, 0, 1.1, 1.9, same_node_threshold=0.2)

    assert result.nodes == {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0}
    assert result.types[0].labels == [AnnotationLabel(1, 2, id=0)]


def test_create_label_custom_threshold_smaller_than_default_adds_nodes():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 2.0}, [[]])
    offset = SAME_NODE_THRESHOLD / 2

    result = create_label(
        annotation, 0, 1.0 + offset, 2.0 - offset, SAME_NODE_THRESHOLD / 4
    )

    assert len(result.nodes) == 5
    assert label_times(result, 0) == [(1.0 + offset, 2.0 - offset, "")]


def test_create_label_snaps_each_end_to_closest_node():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 1.3, 3: 2.0, 4: 3.0}, [[]])

    result = create_label(annotation, 0, 1.05, 2.0, same_node_threshold=0.35)

    assert result.types[0].labels == [AnnotationLabel(1, 3, id=0)]


def test_create_label_raises_when_both_ends_snap_to_same_node():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 3.0}, [[]])

    with pytest.raises(ZeroLengthLabelError):
        create_label(annotation, 0, 1.05, 1.2, same_node_threshold=0.35)


def test_create_label_raises_when_selection_shorter_than_threshold():
    annotation = make_annotation({0: 0.0, 1: 3.0}, [[]])

    with pytest.raises(ZeroLengthLabelError):
        create_label(annotation, 0, 1.5, 1.6, same_node_threshold=0.2)


def test_zero_length_label_error_is_value_error():
    assert issubclass(ZeroLengthLabelError, ValueError)
