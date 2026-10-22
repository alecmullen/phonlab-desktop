from core.annotation.entity.annotation import (
    AnnotationLabel,
    add_node_time,
    get_matching_node,
)
from res.constants import SAME_NODE_THRESHOLD


def test_annotation_label_defaults_to_empty_text():
    assert AnnotationLabel(0, 1, 2).label == ""


# --------------------------- get_matching_node ---------------------------


def test_get_matching_node_returns_id_of_exact_match():
    assert get_matching_node({0: 0.0, 1: 0.5, 2: 1.0}, 0.5) == 1


def test_get_matching_node_returns_id_within_threshold_of_next_node():
    nodes = {0: 0.0, 1: 0.5, 2: 1.0}

    assert get_matching_node(nodes, 0.5 - SAME_NODE_THRESHOLD / 2) == 1


def test_get_matching_node_returns_id_within_threshold_of_previous_node():
    nodes = {0: 0.0, 1: 0.5, 2: 1.0}

    assert get_matching_node(nodes, 0.5 + SAME_NODE_THRESHOLD / 2) == 1


def test_get_matching_node_returns_none_beyond_threshold():
    nodes = {0: 0.0, 1: 0.5, 2: 1.0}

    assert get_matching_node(nodes, 0.5 + SAME_NODE_THRESHOLD * 2) is None


def test_get_matching_node_uses_node_ids_when_out_of_time_order():
    nodes = {7: 1.0, 3: 0.0, 5: 0.5}

    assert get_matching_node(nodes, 0.0) == 3
    assert get_matching_node(nodes, 0.5) == 5
    assert get_matching_node(nodes, 1.0) == 7


def test_get_matching_node_matches_past_last_node():
    assert get_matching_node({0: 0.0, 1: 1.0}, 1.0 + SAME_NODE_THRESHOLD / 2) == 1


def test_get_matching_node_matches_before_first_node():
    assert get_matching_node({0: 0.0, 1: 1.0}, -SAME_NODE_THRESHOLD / 2) == 0


# --------------------------- add_node_time ---------------------------


def test_add_node_time_ignores_none():
    assert add_node_time([0.0, 1.0], None) == [0.0, 1.0]


def test_add_node_time_inserts_in_sorted_position():
    assert add_node_time([0.0, 1.0], 0.5) == [0.0, 0.5, 1.0]


def test_add_node_time_skips_time_within_threshold_of_next_node():
    assert add_node_time([0.0, 0.5, 1.0], 0.5 - SAME_NODE_THRESHOLD / 2) == [
        0.0,
        0.5,
        1.0,
    ]


def test_add_node_time_skips_time_within_threshold_of_previous_node():
    assert add_node_time([0.0, 0.5, 1.0], 0.5 + SAME_NODE_THRESHOLD / 2) == [
        0.0,
        0.5,
        1.0,
    ]


def test_add_node_time_keeps_separate_nodes_beyond_threshold():
    new_time = 0.5 + SAME_NODE_THRESHOLD * 2

    assert add_node_time([0.0, 0.5, 1.0], new_time) == [0.0, 0.5, new_time, 1.0]


def test_add_node_time_handles_empty_list():
    assert add_node_time([], 0.25) == [0.25]


# --------------------------- custom threshold ---------------------------


def test_get_matching_node_custom_threshold_matches_beyond_default():
    nodes = {0: 0.0, 1: 1.0}
    offset = SAME_NODE_THRESHOLD * 4

    assert get_matching_node(nodes, 1.0 + offset) is None
    assert get_matching_node(nodes, 1.0 + offset, offset * 2) == 1


def test_get_matching_node_custom_threshold_rejects_within_default():
    nodes = {0: 0.0, 1: 1.0}
    offset = SAME_NODE_THRESHOLD / 2

    assert get_matching_node(nodes, 1.0 - offset) == 1
    assert get_matching_node(nodes, 1.0 - offset, offset / 2) is None


def test_get_matching_node_threshold_is_exclusive():
    assert get_matching_node({0: 0.0, 1: 1.0}, 1.25, 0.25) is None


def test_add_node_time_custom_threshold_skips_time_beyond_default():
    new_time = 0.5 + SAME_NODE_THRESHOLD * 4

    assert add_node_time([0.0, 0.5, 1.0], new_time, SAME_NODE_THRESHOLD * 8) == [
        0.0,
        0.5,
        1.0,
    ]


def test_add_node_time_custom_threshold_inserts_time_within_default():
    new_time = 0.5 + SAME_NODE_THRESHOLD / 2

    assert add_node_time([0.0, 0.5, 1.0], new_time, SAME_NODE_THRESHOLD / 4) == [
        0.0,
        0.5,
        new_time,
        1.0,
    ]


def test_get_matching_node_prefers_closer_previous_node():
    assert get_matching_node({0: 1.0, 1: 1.3}, 1.05, 0.35) == 0


def test_get_matching_node_prefers_closer_next_node():
    assert get_matching_node({0: 1.0, 1: 1.3}, 1.25, 0.35) == 1


def test_get_matching_node_ignores_closer_node_outside_threshold_order():
    # next node is out of range, previous one is in range
    assert get_matching_node({0: 1.0, 1: 2.0}, 1.2, 0.25) == 0


def test_add_node_time_skips_when_either_neighbour_is_within_threshold():
    assert add_node_time([1.0, 1.3], 1.05, 0.35) == [1.0, 1.3]
