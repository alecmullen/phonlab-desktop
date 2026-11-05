from dataclasses import replace

from core.annotation.clear_interval import ClearInterval
from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
)
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync


class ZeroLengthLabelError(ValueError):
    pass


class CreateLabel(UseCaseSync[Annotation]):
    def __init__(
        self, clear_interval: ClearInterval, annotation_repository: AnnotationRepository
    ):
        self.clear_interval = clear_interval
        self.annotation_repository = annotation_repository

    def __call__(
        self,
        annotation: Annotation,
        type_id: int,
        start: float,
        end: float,
        same_node_threshold: float = 0.0,
    ) -> Annotation:
        annotation_id = annotation.get_id()
        s_node, s_time = self.annotation_repository.create_node(
            annotation_id, start, same_node_threshold
        )
        e_node, e_time = self.annotation_repository.create_node(
            annotation_id, end, same_node_threshold
        )

        if s_node == e_node:
            raise ZeroLengthLabelError()

        annotation = replace(
            annotation, nodes=annotation.nodes | {s_node: s_time} | {e_node: e_time}
        )

        annotation = self.clear_interval(annotation, [type_id], s_node, e_node)

        label = self.annotation_repository.create_label(
            AnnotationLabel(s_node, e_node), type_id
        )

        types = [
            type if type.id != type_id else replace(type, labels=type.labels + [label])
            for type in annotation.types
        ]

        return replace(annotation, types=types)
