from core.annotation.entity.annotation import (
    AnnotationLabel,
    get_matching_node,
)
from res.constants import SAME_NODE_THRESHOLD


def test_annotation_label_defaults_to_empty_text():
    assert AnnotationLabel(0, 1).label == ""


# --------------------------- get_matching_node ---------------------------


def test_get_matching_node_returns_id_of_exact_match():
    assert get_matching_node([0.0, 0.5, 1.0], 0.5) == 1


def test_get_matching_node_returns_id_within_threshold_of_next_node():
    nodes = [0.0, 0.5, 1.0]

    assert get_matching_node(nodes, 0.5 - SAME_NODE_THRESHOLD / 2) == 1


def test_get_matching_node_returns_id_within_threshold_of_previous_node():
    nodes = [0.0, 0.5, 1.0]

    assert get_matching_node(nodes, 0.5 + SAME_NODE_THRESHOLD / 2) == 1


def test_get_matching_node_returns_none_beyond_threshold():
    nodes = [0.0, 0.5, 1.0]

    assert get_matching_node(nodes, 0.5 + SAME_NODE_THRESHOLD * 2) is None


def test_get_matching_node_returns_index_without_node_ids():
    assert get_matching_node([0.0, 0.5, 1.0], 1.0) == 2


def test_get_matching_node_maps_index_to_node_ids_when_given():
    times = [0.0, 0.5, 1.0]
    ids = [3, 5, 7]

    assert get_matching_node(times, 0.0, node_ids=ids) == 3
    assert get_matching_node(times, 0.5, node_ids=ids) == 5
    assert get_matching_node(times, 1.0, node_ids=ids) == 7


def test_get_matching_node_returns_none_for_empty_nodes():
    assert get_matching_node([], 0.5) is None


def test_get_matching_node_matches_past_last_node():
    assert get_matching_node([0.0, 1.0], 1.0 + SAME_NODE_THRESHOLD / 2) == 1


def test_get_matching_node_matches_before_first_node():
    assert get_matching_node([0.0, 1.0], -SAME_NODE_THRESHOLD / 2) == 0


# --------------------------- custom threshold ---------------------------


def test_get_matching_node_custom_threshold_matches_beyond_default():
    nodes = [0.0, 1.0]
    offset = SAME_NODE_THRESHOLD * 4

    assert get_matching_node(nodes, 1.0 + offset) is None
    assert get_matching_node(nodes, 1.0 + offset, offset * 2) == 1


def test_get_matching_node_custom_threshold_rejects_within_default():
    nodes = [0.0, 1.0]
    offset = SAME_NODE_THRESHOLD / 2

    assert get_matching_node(nodes, 1.0 - offset) == 1
    assert get_matching_node(nodes, 1.0 - offset, offset / 2) is None


def test_get_matching_node_threshold_is_exclusive():
    assert get_matching_node([0.0, 1.0], 1.25, 0.25) is None


def test_get_matching_node_prefers_closer_previous_node():
    assert get_matching_node([1.0, 1.3], 1.05, 0.35) == 0


def test_get_matching_node_prefers_closer_next_node():
    assert get_matching_node([1.0, 1.3], 1.25, 0.35) == 1


def test_get_matching_node_ignores_closer_node_outside_threshold_order():
    # next node is out of range, previous one is in range
    assert get_matching_node([1.0, 2.0], 1.2, 0.25) == 0
