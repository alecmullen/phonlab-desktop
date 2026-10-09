import bisect

import phonlab as phon

from core.base.use_case_sync import UseCaseSync
from core.parse_textgrid.annotation import Annotation, AnnotationLabel, AnnotationType

SAME_NODE_THRESHOLD = 0.005
INTERVAL_TIER_NAME = "IntervalTier"
POINT_TIER_NAME = "TextTier"


class ParseTextGridError(ValueError):
    pass


class ParseTextGrid(UseCaseSync):
    def __init__(self, filename: str):
        super().__init__()
        self.filename = filename

    def invoke(self) -> Annotation:
        try:
            tiers = phon.read_textgrid_with(self.filename)

            node_times: list[float] = []
            for tier in tiers:
                for label in tier["labels"]:
                    node_times = add_node_time(node_times, label[0])
                    node_times = add_node_time(node_times, label[1])
            return Annotation(
                nodes={idx: node for idx, node in enumerate(node_times)},
                types=[
                    AnnotationType(
                        tier["name"],
                        [to_label(node_times, label) for label in tier["labels"]],
                    )
                    for tier in tiers
                ],
            )
        except Exception as err:
            raise ParseTextGridError from err


def add_node_time(node_times: list[float], new_time: float | None) -> list[float]:
    if new_time is None:
        return node_times

    idx = bisect.bisect_left(node_times, new_time)

    if (
        idx < len(node_times) and abs(node_times[idx] - new_time) < SAME_NODE_THRESHOLD
    ) or (idx - 1 >= 0 and abs(node_times[idx - 1] - new_time) < SAME_NODE_THRESHOLD):
        return node_times

    bisect.insort(node_times, new_time)
    return node_times


def to_label(node_times: list[float], label: tuple) -> AnnotationLabel:
    s_node = bisect.bisect_left(node_times, label[0])
    if label[1] is None:
        e_node = s_node
    else:
        e_node = bisect.bisect_left(node_times, label[1])
    return AnnotationLabel(s_node, e_node, label[2])
