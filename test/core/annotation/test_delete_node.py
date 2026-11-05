import pytest

from support.annotation_repository import FakeAnnotationRepository

from core.annotation.delete_node import DeleteNodeError, DeleteNode
from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
)


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


def delete_node(annotation: Annotation, node: int) -> Annotation:
    repository = FakeAnnotationRepository()
    return DeleteNode(repository)(repository.seed(annotation), node)


def label_spans(annotation: Annotation, tier: int) -> list[tuple]:
    return sorted(
        (label.s_node, label.e_node, label.label)
        for label in annotation.types[tier].labels
    )


def test_delete_node_missing_node_raises_value_error():
    annotation = make_annotation({0: 0.0, 1: 1.0}, [[(0, 1, "a")]])

    with pytest.raises(ValueError):
        delete_node(annotation, 99)


def test_delete_node_merges_adjacent_labels_keeping_first_id():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a"), (1, 2, "b")]])

    result = delete_node(annotation, 1)

    assert result.types[0].labels == [AnnotationLabel(0, 2, "ab", id=0)]
    assert result.nodes == {0: 0.0, 2: 2.0}


def test_delete_node_removes_point_label():
    annotation = make_annotation({0: 0.5, 1: 1.5}, [[(0, 0, "x"), (1, 1, "y")]])

    result = delete_node(annotation, 0)

    assert label_spans(result, 0) == [(1, 1, "y")]


def test_delete_node_with_label_on_only_one_side_raises():
    annotation = make_annotation(
        {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0}, [[(0, 1, "a"), (2, 3, "b")]]
    )

    with pytest.raises(DeleteNodeError):
        delete_node(annotation, 1)


def test_delete_node_leaves_tiers_without_node_untouched():
    annotation = make_annotation(
        {0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a"), (1, 2, "b")], [(0, 2, "c")]]
    )

    result = delete_node(annotation, 1)

    assert label_spans(result, 1) == [(0, 2, "c")]


def test_delete_node_merges_labels_on_every_tier_at_node():
    annotation = make_annotation(
        {0: 0.0, 1: 1.0, 2: 2.0},
        [[(0, 1, "a"), (1, 2, "b")], [(0, 1, "c"), (1, 2, "d")]],
    )

    result = delete_node(annotation, 1)

    assert label_spans(result, 0) == [(0, 2, "ab")]
    assert label_spans(result, 1) == [(0, 2, "cd")]


def test_delete_node_with_ids_out_of_time_order():
    annotation = make_annotation(
        {5: 0.0, 3: 1.0, 0: 2.0, 1: 3.0}, [[(5, 3, "a"), (3, 0, "b"), (0, 1, "c")]]
    )

    result = delete_node(annotation, 3)

    assert label_spans(result, 0) == [(0, 1, "c"), (5, 0, "ab")]


def test_delete_last_node_of_tier_with_attached_label_raises():
    annotation = make_annotation(
        {0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a")], [(0, 2, "b")]]
    )

    with pytest.raises(DeleteNodeError):
        delete_node(annotation, 1)


@pytest.mark.parametrize("node", [0, 2])
def test_delete_end_node_with_attached_label_raises(node: int):
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a"), (1, 2, "b")]])

    with pytest.raises(DeleteNodeError):
        delete_node(annotation, node)


def test_delete_end_node_error_is_value_error():
    assert issubclass(DeleteNodeError, ValueError)


def test_delete_node_does_not_mutate_input():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a"), (1, 2, "b")]])
    original_labels = list(annotation.types[0].labels)

    delete_node(annotation, 1)

    assert annotation.types[0].labels == original_labels
    assert 1 in annotation.nodes
