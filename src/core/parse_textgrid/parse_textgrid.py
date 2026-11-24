import bisect

from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
    add_node_time,
    get_matching_node,
)
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case import UseCase
from core.read_tiers.entity.table_format import TierFile
from core.read_tiers.read_tier_table import read_tier_table
from core.read_tiers.read_tiers import read_tiers
from res.constants import SAME_NODE_THRESHOLD


class ParseTextGridError(ValueError):
    pass


class ParseTextGrid(UseCase[Annotation]):
    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(
        self,
        file_path: str | None,
        file_stem: str,
        overwrite: bool = False,
        tier_files: dict[str, TierFile] | None = None,
        audio_path: str | None = None,
    ):
        """Replaces any existing content for file_stem only if overwrite is True. The
        files are read before anything in the database is touched, so an unreadable
        TextGrid leaves the existing annotation as it was.

        The annotation is the tiers of the TextGrid (if there is one) and a tier for
        each of `tier_files` (tier name -> a text table of intervals and how to read it),
        read with the help of the length of the audio file `audio_path`. A tier that
        says who produced it keeps that as its talker."""
        try:
            tiers = read_tiers(file_path) if file_path else []
            tiers += [
                read_tier_table(tier.path, name, audio_path, tier.table)
                for name, tier in (tier_files or {}).items()
            ]

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

            times, ids = list(node_times_db), list(node_ids_db)
            types = [
                AnnotationType(
                    tier["name"],
                    [to_label(times, ids, label) for label in tier["labels"]],
                    talker=tier.get("talker"),
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
    """The label with the nodes at its times. Times of different tiers that are
    nearly the same share a node, so the node is the one nearest the time"""
    s_node = _node_at(node_times, node_ids, label[0])
    e_node = s_node if label[1] is None else _node_at(node_times, node_ids, label[1])
    return AnnotationLabel(s_node, e_node, label[2])


def _node_at(node_times: list[float], node_ids: list[int], time: float) -> int:
    node = get_matching_node(node_times, time, node_ids=node_ids)
    if node is None:
        node = node_ids[min(bisect.bisect_left(node_times, time), len(node_ids) - 1)]
    return node
