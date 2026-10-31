import bisect
from pathlib import Path

import phonlab as phon

from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
    add_node_time,
)
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync

INTERVAL_TIER_NAME = "IntervalTier"
POINT_TIER_NAME = "TextTier"


class ParseTextGridError(ValueError):
    pass


class ParseTextGrid(UseCaseSync[Annotation]):
    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(self, filename: str) -> Annotation:
        try:
            file_stem = Path(filename).stem
            id = self.annotation_repository.create_annotation(file_stem)

            tiers = phon.read_textgrid_with(filename)

            node_times: list[float] = []
            for tier in tiers:
                for label in tier["labels"]:
                    node_times = add_node_time(node_times, label[0])
                    node_times = add_node_time(node_times, label[1])

            nodes = self.annotation_repository.create_nodes(id, node_times)
            node_ids_db, node_times_db = zip(
                *sorted(nodes.items(), key=lambda item: item[1])
            )

            types = [
                AnnotationType(
                    tier["name"],
                    [
                        to_label(list(node_times_db), list(node_ids_db), label)
                        for label in tier["labels"]
                    ],
                )
                for tier in tiers
            ]
            self.annotation_repository.create_types(id, types)

            return self.annotation_repository.get_annotation_by_id(id)
        except Exception as err:
            raise ParseTextGridError from err


def to_label(
    node_times: list[float], node_ids: list[int], label: tuple
) -> AnnotationLabel:
    s_node_idx = bisect.bisect_left(node_times, label[0])
    if label[1] is None:
        e_node_idx = s_node_idx
    else:
        e_node_idx = bisect.bisect_left(node_times, label[1])
    return AnnotationLabel(node_ids[s_node_idx], node_ids[e_node_idx], label[2])
