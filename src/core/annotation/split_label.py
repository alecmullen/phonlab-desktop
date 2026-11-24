from dataclasses import replace

from core.annotation.entity.annotation import Annotation, AnnotationLabel
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync


class NoConnectedLabelError(Exception):
    pass


class SplitLabel(UseCaseSync[Annotation]):
    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(
        self, annotation: Annotation, type_ids: list[int], time: float
    ) -> Annotation:
        annotation_id = annotation.get_id()
        node_id, time = self.annotation_repository.create_node(annotation_id, time, 0)

        types = []
        is_connected_label = False
        for type in annotation.types:
            if not type.id in type_ids:
                types.append(type)
                continue

            labels = []
            for label in type.labels:
                start, end = (
                    annotation.nodes[label.s_node],
                    annotation.nodes[label.e_node],
                )
                if start > time or end < time:
                    labels.append(label)
                elif start == time or end == time:
                    raise ValueError("Node already exists at this exact time")
                else:
                    updated_labels = self._split_label(label, type.get_id(), node_id)
                    labels.extend(updated_labels)
                    is_connected_label = True

            types.append(replace(type, labels=labels))

        if not is_connected_label:
            raise NoConnectedLabelError("No label to split")

        return replace(
            annotation, nodes=annotation.nodes | {node_id: time}, types=types
        )

    def _split_label(
        self,
        label: AnnotationLabel,
        type_id: int,
        node_id: int,
    ) -> list[AnnotationLabel]:

        left_label = replace(label, e_node=node_id)
        self.annotation_repository.update_label(left_label)

        right_label = self.annotation_repository.create_label(
            AnnotationLabel(s_node=node_id, e_node=label.e_node),
            type_id,
        )

        return [left_label, right_label]
