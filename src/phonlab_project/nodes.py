"""Nodes shared between tiers. A point in time of a recording is one node however many
labels begin or end there, and times of different tiers that are nearly the same (within
SAME_NODE_THRESHOLD seconds) are one node, so that moving it moves the boundary of every
tier that has it."""

import bisect

from phonlab_project.constants import SAME_NODE_THRESHOLD


def get_matching_node(
    node_times: list[float],
    new_time: float,
    same_node_threshold: float | None = None,
    node_ids: list[int] | None = None,
) -> int | None:
    """Searches for the node closest to new_time, if within threshold. node_times and
    node_ids must be sorted by node time. If node_ids is None, uses index of sorted
    node_times"""
    if same_node_threshold is None:
        same_node_threshold = SAME_NODE_THRESHOLD

    idx = bisect.bisect_left(node_times, new_time)

    candidates = [i for i in (idx, idx - 1) if 0 <= i < len(node_times)]
    if len(candidates) == 0:
        return None

    closest = min(candidates, key=lambda i: abs(node_times[i] - new_time))
    if abs(node_times[closest] - new_time) >= same_node_threshold:
        return None

    return node_ids[closest] if node_ids is not None else closest


def add_node_time(
    node_times: list[float],
    new_time: float | None,
    same_node_threshold: float | None = None,
) -> list[float]:
    if new_time is None:
        return node_times

    node = get_matching_node(node_times, new_time, same_node_threshold)

    if node is None:
        bisect.insort(node_times, new_time)

    return node_times


def node_at(node_times: list[float], node_ids: list[int], time: float) -> int:
    """The id of the node at `time`: the one within the threshold, else the nearest.
    `node_times` and `node_ids` are sorted by time and not empty."""
    node = get_matching_node(node_times, time, node_ids=node_ids)
    if node is None:
        node = node_ids[min(bisect.bisect_left(node_times, time), len(node_ids) - 1)]
    return node
