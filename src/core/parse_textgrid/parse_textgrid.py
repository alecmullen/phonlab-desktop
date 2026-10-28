import bisect

import phonlab as phon

from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
    add_node_time,
)
from core.base.use_case_sync import UseCaseSync

INTERVAL_TIER_NAME = "IntervalTier"
POINT_TIER_NAME = "TextTier"


class ParseTextGridError(ValueError):
    pass


class ParseTextGrid(UseCaseSync[Annotation]):
    def __call__(self, filename: str) -> Annotation:
        try:
            tiers = phon.read_textgrid_with(filename)

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
                        [
                            to_label(node_times, idx, label)
                            for idx, label in enumerate(tier["labels"])
                        ],
                    )
                    for tier in tiers
                ],
            )
        except Exception as err:
            raise ParseTextGridError from err


def to_label(node_times: list[float], id: int, label: tuple) -> AnnotationLabel:
    s_node = bisect.bisect_left(node_times, label[0])
    if label[1] is None:
        e_node = s_node
    else:
        e_node = bisect.bisect_left(node_times, label[1])
    return AnnotationLabel(id, s_node, e_node, label[2])
