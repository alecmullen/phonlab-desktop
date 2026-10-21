from core.annotation.create_node import create_node
from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
)
from res.constants import SAME_NODE_THRESHOLD


def test_create_node_adds_new_node_with_next_id():
    annotation = Annotation(nodes={0: 0.0, 1: 1.0})

    result, node = create_node(annotation, 0.5)

    assert node == 2
    assert result.nodes == {0: 0.0, 1: 1.0, 2: 0.5}


def test_create_node_new_id_is_max_id_plus_one():
    annotation = Annotation(nodes={3: 0.0, 9: 1.0})

    result, node = create_node(annotation, 0.5)

    assert node == 10
    assert result.nodes[10] == 0.5


def test_create_node_reuses_existing_node_within_threshold():
    annotation = Annotation(nodes={0: 0.0, 1: 1.0})

    result, node = create_node(annotation, 1.0 - SAME_NODE_THRESHOLD / 2)

    assert node == 1
    assert result.nodes == {0: 0.0, 1: 1.0}


def test_create_node_on_empty_annotation_creates_first_node():
    result, node = create_node(Annotation(), 0.5)

    assert node == 0
    assert result.nodes == {0: 0.5}


def test_create_node_keeps_types():
    types = [AnnotationType("word", [AnnotationLabel(0, 0, 1, "a")])]
    annotation = Annotation(nodes={0: 0.0, 1: 1.0}, types=types)

    result, _ = create_node(annotation, 0.5)

    assert result.types == types


def test_create_node_does_not_mutate_input():
    annotation = Annotation(nodes={0: 0.0, 1: 1.0})

    create_node(annotation, 0.5)

    assert annotation.nodes == {0: 0.0, 1: 1.0}
