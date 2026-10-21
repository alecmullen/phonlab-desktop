from core.annotation.create_label import CreateLabel
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
                [AnnotationLabel(id, *label) for id, label in enumerate(labels)],
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

    result = CreateLabel(annotation, 0, 1.0, 2.0).invoke()

    assert result.nodes == {0: 0.0, 1: 3.0, 2: 1.0, 3: 2.0}
    assert result.types[0].labels == [AnnotationLabel(0, 2, 3, "")]


def test_create_label_reuses_nodes_within_threshold():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 2.0}, [[(0, 1, "a")]])

    result = CreateLabel(
        annotation, 0, 1.0 + SAME_NODE_THRESHOLD / 2, 2.0 - SAME_NODE_THRESHOLD / 2
    ).invoke()

    assert result.nodes == {0: 0.0, 1: 1.0, 2: 2.0}
    assert label_times(result, 0) == [(0.0, 1.0, "a"), (1.0, 2.0, "")]


def test_create_label_id_is_max_id_plus_one():
    annotation = Annotation(
        nodes={0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0},
        types=[AnnotationType("word", [AnnotationLabel(5, 0, 1, "a")])],
    )

    result = CreateLabel(annotation, 0, 2.0, 3.0).invoke()

    assert [label.id for label in result.types[0].labels] == [5, 6]


def test_create_label_replaces_labels_inside_selection():
    annotation = make_annotation(
        {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0}, [[(0, 1, "a"), (1, 2, "b"), (2, 3, "c")]]
    )

    result = CreateLabel(annotation, 0, 0.5, 2.5).invoke()

    assert label_times(result, 0) == [
        (0.0, 0.5, "a"),
        (0.5, 2.5, ""),
        (2.5, 3.0, "c"),
    ]


def test_create_label_inside_existing_label_splits_it():
    annotation = make_annotation({0: 0.0, 1: 3.0}, [[(0, 1, "a")]])

    result = CreateLabel(annotation, 0, 1.0, 2.0).invoke()

    assert label_times(result, 0) == [
        (0.0, 1.0, "a"),
        (1.0, 2.0, ""),
        (2.0, 3.0, ""),
    ]


def test_create_label_only_changes_target_tier():
    annotation = make_annotation(
        {0: 0.0, 1: 3.0}, [[(0, 1, "a")], [(0, 1, "b")], [(0, 1, "c")]]
    )

    result = CreateLabel(annotation, 1, 1.0, 2.0).invoke()

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

    CreateLabel(annotation, 0, 1.0, 2.0).invoke()

    assert annotation.nodes == {0: 0.0, 1: 3.0}
    assert annotation.types[0].labels == original_labels


def test_create_label_splitting_label_gives_unique_ids():
    annotation = make_annotation({0: 0.0, 1: 3.0}, [[(0, 1, "a")]])

    result = CreateLabel(annotation, 0, 1.0, 2.0).invoke()

    ids = [label.id for label in result.types[0].labels]
    assert len(ids) == len(set(ids))


def test_delete_node_after_splitting_label_merges_with_new_label():
    annotation = make_annotation({0: 0.0, 1: 3.0}, [[(0, 1, "a")]])
    annotation = CreateLabel(annotation, 0, 1.0, 2.0).invoke()

    result = DeleteNode(annotation, 2).invoke()

    assert label_times(result, 0) == [(0.0, 2.0, "a"), (2.0, 3.0, "")]
