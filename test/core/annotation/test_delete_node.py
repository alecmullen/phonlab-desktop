import pytest

from core.annotation.delete_node import DeleteEndNodeError, DeleteNode
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


def label_spans(annotation: Annotation, tier: int) -> list[tuple]:
    return sorted(
        (label.s_node, label.e_node, label.label)
        for label in annotation.types[tier].labels
    )


def test_delete_node_missing_node_raises_value_error():
    annotation = make_annotation({0: 0.0, 1: 1.0}, [[(0, 1, "a")]])

    with pytest.raises(ValueError):
        DeleteNode()(annotation, 99)


def test_delete_node_merges_adjacent_labels_keeping_first_id():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a"), (1, 2, "b")]])

    result = DeleteNode()(annotation, 1)

    assert result.types[0].labels == [AnnotationLabel(0, 2, "ab", id=0)]
    assert result.nodes == {0: 0.0, 2: 2.0}


def test_delete_node_removes_point_label():
    annotation = make_annotation({0: 0.5, 1: 1.5}, [[(0, 0, "x"), (1, 1, "y")]])

    result = DeleteNode()(annotation, 0)

    assert label_spans(result, 0) == [(1, 1, "y")]


def test_delete_node_extends_label_to_next_node_on_tier():
    annotation = make_annotation(
        {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0}, [[(0, 1, "a"), (2, 3, "b")]]
    )

    result = DeleteNode()(annotation, 1)

    assert label_spans(result, 0) == [(0, 2, "a"), (2, 3, "b")]


def test_delete_node_leaves_tiers_without_node_untouched():
    annotation = make_annotation(
        {0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a"), (1, 2, "b")], [(0, 2, "c")]]
    )

    result = DeleteNode()(annotation, 1)

    assert label_spans(result, 1) == [(0, 2, "c")]


def test_delete_node_merges_labels_on_every_tier_at_node():
    annotation = make_annotation(
        {0: 0.0, 1: 1.0, 2: 2.0},
        [[(0, 1, "a"), (1, 2, "b")], [(0, 1, "c"), (1, 2, "d")]],
    )

    result = DeleteNode()(annotation, 1)

    assert label_spans(result, 0) == [(0, 2, "ab")]
    assert label_spans(result, 1) == [(0, 2, "cd")]


def test_delete_node_with_ids_out_of_time_order():
    annotation = make_annotation(
        {5: 0.0, 3: 1.0, 0: 2.0, 1: 3.0}, [[(5, 3, "a"), (0, 1, "b")]]
    )

    result = DeleteNode()(annotation, 3)

    assert label_spans(result, 0) == [(0, 1, "b"), (5, 0, "a")]


def test_delete_last_node_of_tier_with_attached_label_raises():
    annotation = make_annotation(
        {0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a")], [(0, 2, "b")]]
    )

    with pytest.raises(DeleteEndNodeError):
        DeleteNode()(annotation, 1)


@pytest.mark.parametrize("node", [0, 2])
def test_delete_end_node_with_attached_label_raises(node: int):
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a"), (1, 2, "b")]])

    with pytest.raises(DeleteEndNodeError):
        DeleteNode()(annotation, node)


def test_delete_end_node_error_is_value_error():
    assert issubclass(DeleteEndNodeError, ValueError)


def test_delete_node_does_not_mutate_input():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a"), (1, 2, "b")]])
    original_labels = list(annotation.types[0].labels)

    DeleteNode()(annotation, 1)

    assert annotation.types[0].labels == original_labels
    assert 1 in annotation.nodes
