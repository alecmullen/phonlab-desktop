import bisect
from dataclasses import dataclass, field

from res.constants import SAME_NODE_THRESHOLD
from ui.base.state import State


@dataclass(frozen=True)
class AnnotationLabel(State):
    id: int
    s_node: int
    e_node: int
    label: str = ""


@dataclass(frozen=True)
class AnnotationType(State):
    type: str
    labels: list[AnnotationLabel]


@dataclass(frozen=True)
class Annotation(State):
    nodes: dict[int, float] = field(default_factory=dict)
    types: list[AnnotationType] = field(default_factory=list)


def get_matching_node(
    nodes: dict[int, float], new_time: float, same_node_threshold: float | None = None
) -> int | None:
    if len(nodes) == 0:
        return None

    node_ids: tuple[int]
    node_times: tuple[float]
    node_ids, node_times = zip(*sorted(nodes.items(), key=lambda item: item[1]))
    return _get_matching_node(
        list(node_times), new_time, same_node_threshold, list(node_ids)
    )


def _get_matching_node(
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

    node = _get_matching_node(node_times, new_time, same_node_threshold)

    if node is None:
        bisect.insort(node_times, new_time)

    return node_times
