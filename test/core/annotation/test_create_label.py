import pytest

from core.annotation.create_label import CreateLabel, ZeroLengthLabelError
from core.annotation.delete_node import DeleteNode
from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
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


def label_times(annotation: Annotation, tier: int) -> list[tuple]:
    nodes = annotation.nodes
    return sorted(
        (nodes[label.s_node], nodes[label.e_node], label.label)
        for label in annotation.types[tier].labels
    )


def test_create_label_on_empty_tier_creates_nodes_and_label():
    annotation = make_annotation({0: 0.0, 1: 3.0}, [[]])

    result = CreateLabel()(annotation, 0, 1.0, 2.0)

    assert result.nodes == {0: 0.0, 1: 3.0, 2: 1.0, 3: 2.0}
    assert result.types[0].labels == [AnnotationLabel(2, 3)]


def test_create_label_reuses_nodes_within_threshold():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a")]])

    result = CreateLabel()(
        annotation, 0, 1.0 + SAME_NODE_THRESHOLD / 2, 2.0 - SAME_NODE_THRESHOLD / 2
    )

    assert result.nodes == {0: 0.0, 1: 1.0, 2: 2.0}
    assert label_times(result, 0) == [(0.0, 1.0, "a"), (1.0, 2.0, "")]


def test_create_label_has_no_id_until_saved():
    annotation = Annotation(
        nodes={0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0},
        types=[AnnotationType("word", [AnnotationLabel(0, 1, "a", id=5)])],
    )

    result = CreateLabel()(annotation, 0, 2.0, 3.0)

    assert [label.id for label in result.types[0].labels] == [5, None]


def test_create_label_replaces_labels_inside_selection():
    annotation = make_annotation(
        {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0}, [[(0, 1, "a"), (1, 2, "b"), (2, 3, "c")]]
    )

    result = CreateLabel()(annotation, 0, 0.5, 2.5)

    assert label_times(result, 0) == [
        (0.0, 0.5, "a"),
        (0.5, 2.5, ""),
        (2.5, 3.0, "c"),
    ]


def test_create_label_inside_existing_label_splits_it():
    annotation = make_annotation({0: 0.0, 1: 3.0}, [[(0, 1, "a")]])

    result = CreateLabel()(annotation, 0, 1.0, 2.0)

    assert label_times(result, 0) == [
        (0.0, 1.0, "a"),
        (1.0, 2.0, ""),
        (2.0, 3.0, ""),
    ]


def test_create_label_only_changes_target_tier():
    annotation = make_annotation(
        {0: 0.0, 1: 3.0}, [[(0, 1, "a")], [(0, 1, "b")], [(0, 1, "c")]]
    )

    result = CreateLabel()(annotation, 1, 1.0, 2.0)

    assert result.types[0] == annotation.types[0]
    assert result.types[2] == annotation.types[2]
    assert label_times(result, 1) == [
        (0.0, 1.0, "b"),
        (1.0, 2.0, ""),
        (2.0, 3.0, ""),
    ]


def test_create_label_does_not_mutate_input():
    annotation = make_annotation({0: 0.0, 1: 3.0}, [[(0, 1, "a")]])
    original_labels = list(annotation.types[0].labels)

    CreateLabel()(annotation, 0, 1.0, 2.0)

    assert annotation.nodes == {0: 0.0, 1: 3.0}
    assert annotation.types[0].labels == original_labels


def test_create_label_splitting_label_leaves_new_labels_without_ids():
    annotation = make_annotation({0: 0.0, 1: 3.0}, [[(0, 1, "a")]])

    result = CreateLabel()(annotation, 0, 1.0, 2.0)

    ids = [label.id for label in result.types[0].labels]
    assert sorted(ids, key=lambda id: id is not None) == [None, None, 0]


def test_delete_node_after_splitting_label_merges_with_new_label():
    annotation = make_annotation({0: 0.0, 1: 3.0}, [[(0, 1, "a")]])
    annotation = CreateLabel()(annotation, 0, 1.0, 2.0)

    result = DeleteNode()(annotation, 2)

    assert label_times(result, 0) == [(0.0, 2.0, "a"), (2.0, 3.0, "")]


def test_create_label_custom_threshold_snaps_both_ends_to_existing_nodes():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0}, [[]])

    result = CreateLabel()(annotation, 0, 1.1, 1.9, same_node_threshold=0.2)

    assert result.nodes == {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0}
    assert result.types[0].labels == [AnnotationLabel(1, 2)]


def test_create_label_custom_threshold_smaller_than_default_adds_nodes():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 2.0}, [[]])
    offset = SAME_NODE_THRESHOLD / 2

    result = CreateLabel()(
        annotation, 0, 1.0 + offset, 2.0 - offset, SAME_NODE_THRESHOLD / 4
    )

    assert len(result.nodes) == 5
    assert label_times(result, 0) == [(1.0 + offset, 2.0 - offset, "")]


def test_create_label_snaps_each_end_to_closest_node():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 1.3, 3: 2.0, 4: 3.0}, [[]])

    result = CreateLabel()(annotation, 0, 1.05, 2.0, same_node_threshold=0.35)

    assert result.types[0].labels == [AnnotationLabel(1, 3)]


def test_create_label_raises_when_both_ends_snap_to_same_node():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 3.0}, [[]])

    with pytest.raises(ZeroLengthLabelError):
        CreateLabel()(annotation, 0, 1.05, 1.2, same_node_threshold=0.35)


def test_create_label_raises_when_selection_shorter_than_threshold():
    annotation = make_annotation({0: 0.0, 1: 3.0}, [[]])

    with pytest.raises(ZeroLengthLabelError):
        CreateLabel()(annotation, 0, 1.5, 1.6, same_node_threshold=0.2)


def test_zero_length_label_error_is_value_error():
    assert issubclass(ZeroLengthLabelError, ValueError)
