import bisect
from dataclasses import dataclass, field

from res.constants import SAME_NODE_THRESHOLD
from ui.base.state import State


@dataclass(frozen=True)
class AnnotationLabel(State):
    s_node: int
    e_node: int
    label: str


@dataclass(frozen=True)
class AnnotationType(State):
    type: str
    labels: list[AnnotationLabel]


@dataclass(frozen=True)
class Annotation(State):
    nodes: dict[int, float] = field(default_factory=dict)
    types: list[AnnotationType] = field(default_factory=list)


def get_matching_node(nodes: dict[int, float], new_time: float) -> int | None:
    node_ids, node_times = zip(*sorted(nodes.items(), key=lambda item: item[1]))
    return _get_matching_node(node_ids, node_times, new_time)


def _get_matching_node(
    node_ids: list[int], node_times: list[float], new_time: float
) -> int | None:
    """Searches for node with timestamp within threshold of new_time. node_times and node_ids
    must be sorted by node time"""
    idx = bisect.bisect_left(node_times, new_time)

    if idx < len(node_times) and abs(node_times[idx] - new_time) < SAME_NODE_THRESHOLD:
        return node_ids[idx]
    if idx - 1 >= 0 and abs(node_times[idx - 1] - new_time) < SAME_NODE_THRESHOLD:
        return node_ids[idx - 1]

    return None


def add_node_time(node_times: list[float], new_time: float | None) -> list[float]:
    if new_time is None:
        return node_times

    node = _get_matching_node(range(len(node_times)), node_times, new_time)

    if node is None:
        bisect.insort(node_times, new_time)

    return node_times


def to_label(node_times: list[float], label: tuple) -> AnnotationLabel:
    s_node = bisect.bisect_left(node_times, label[0])
    if label[1] is None:
        e_node = s_node
    else:
        e_node = bisect.bisect_left(node_times, label[1])
    return AnnotationLabel(s_node, e_node, label[2])
