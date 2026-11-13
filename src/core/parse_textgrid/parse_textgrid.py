import bisect

import phonlab as phon

from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
    add_node_time,
)
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case import UseCase
from res.constants import SAME_NODE_THRESHOLD


class ParseTextGridError(ValueError):
    pass


class ParseTextGrid(UseCase[Annotation]):
    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(self, file_path: str, file_stem: str, overwrite: bool = False):
        """Replaces any existing content for file_stem only if overwrite is True"""
        try:
            existing = self.annotation_repository.find_annotation_by_file_stem(
                file_stem
            )
            if existing is None:
                id = self.annotation_repository.create_annotation(file_stem)
            else:
                id = existing.get_id()
                if existing.nodes or existing.types:
                    if not overwrite:
                        raise ValueError(
                            "Annotation for this file already exists in project database"
                        )
                    self.annotation_repository.clear_annotation(id)
                # Otherwise the annotation has no content yet (a stem that was added
                # without a TextGrid, or left behind by a parse that failed part-way),
                # so fill it in

            tiers = phon.read_textgrid_with(file_path)

            node_times: list[float] = []
            for tier in tiers:
                for label in tier["labels"]:
                    node_times = add_node_time(node_times, label[0])
                    node_times = add_node_time(node_times, label[1])

            nodes = self.annotation_repository.create_nodes(
                id, node_times, SAME_NODE_THRESHOLD
            )
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

            yield self.annotation_repository.get_annotation_by_id(id)
        except Exception as err:
            print(err)
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
