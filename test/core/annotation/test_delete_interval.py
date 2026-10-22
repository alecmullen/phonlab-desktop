from core.annotation.delete_interval import delete_annotation_interval
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
                [AnnotationLabel(id, *label) for id, label in enumerate(labels)],
            )
            for idx, labels in enumerate(tiers)
        ],
    )


def label_spans(annotation: Annotation, tier: int) -> list[tuple]:
    return sorted(
        (label.s_node, label.e_node, label.label)
        for label in annotation.types[tier].labels
    )


def test_delete_interval_keeps_labels_outside_interval():
    annotation = make_annotation(
        {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0, 4: 4.0, 5: 5.0},
        [[(0, 1, "a"), (4, 5, "b")]],
    )

    result = delete_annotation_interval(annotation, [0], 2, 3)

    assert label_spans(result, 0) == [(0, 1, "a"), (4, 5, "b")]


def test_delete_interval_keeps_labels_touching_interval_boundaries():
    annotation = make_annotation(
        {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0}, [[(0, 1, "a"), (2, 3, "b")]]
    )

    result = delete_annotation_interval(annotation, [0], 1, 2)

    assert label_spans(result, 0) == [(0, 1, "a"), (2, 3, "b")]


def test_delete_interval_removes_labels_inside_interval():
    annotation = make_annotation(
        {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0},
        [[(1, 2, "a"), (2, 2, "point")]],
    )

    result = delete_annotation_interval(annotation, [0], 0, 3)

    assert label_spans(result, 0) == []


def test_delete_interval_trims_label_overlapping_start():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0}, [[(0, 2, "a")]])

    result = delete_annotation_interval(annotation, [0], 1, 3)

    assert label_spans(result, 0) == [(0, 1, "a")]


def test_delete_interval_trims_label_overlapping_end():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0}, [[(1, 3, "a")]])

    result = delete_annotation_interval(annotation, [0], 0, 2)

    assert label_spans(result, 0) == [(2, 3, "a")]


def test_delete_interval_splits_label_spanning_interval_keeping_text_on_left():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0}, [[(0, 3, "a")]])

    result = delete_annotation_interval(annotation, [0], 1, 2)

    assert label_spans(result, 0) == [(0, 1, "a"), (2, 3, "")]


def test_delete_interval_only_changes_selected_tiers():
    annotation = make_annotation(
        {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0},
        [[(0, 3, "a")], [(0, 3, "b")], [(0, 3, "c")]],
    )

    result = delete_annotation_interval(annotation, [0, 2], 1, 2)

    assert label_spans(result, 0) == [(0, 1, "a"), (2, 3, "")]
    assert label_spans(result, 1) == [(0, 3, "b")]
    assert label_spans(result, 2) == [(0, 1, "c"), (2, 3, "")]
    assert [t.type for t in result.types] == ["tier0", "tier1", "tier2"]


def test_delete_interval_keeps_nodes():
    nodes = {0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0}
    annotation = make_annotation(nodes, [[(1, 2, "a")]])

    result = delete_annotation_interval(annotation, [0], 0, 3)

    assert result.nodes == nodes


def test_delete_interval_does_not_mutate_input():
    annotation = make_annotation({0: 0.0, 1: 1.0, 2: 2.0, 3: 3.0}, [[(0, 3, "a")]])
    original_labels = list(annotation.types[0].labels)

    delete_annotation_interval(annotation, [0], 1, 2)

    assert annotation.types[0].labels == original_labels
