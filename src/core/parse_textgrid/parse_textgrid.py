import phonlab as phon

from core.base.use_case_sync import UseCaseSync
from core.parse_textgrid.annotation import (
    Annotation,
    AnnotationType,
    add_node_time,
    to_label,
)

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
