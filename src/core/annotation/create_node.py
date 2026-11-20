from dataclasses import replace

from core.annotation.entity.annotation import Annotation, AnnotationLabel
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync


class CreateNode(UseCaseSync[Annotation]):
    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(
        self, annotation: Annotation, type_ids: list[int], time: float
    ) -> Annotation:
        annotation_id = annotation.get_id()
        node_id, time = self.annotation_repository.create_node(annotation_id, time, 0)

        types = []
        for type in annotation.types:
            if not type.id in type_ids:
                types.append(type)
                continue

            labels = []
            for label in type.labels:
                updated_labels = self._update_label(
                    label, type.get_id(), annotation.nodes, node_id, time
                )
                labels.extend(updated_labels)

            types.append(replace(type, labels=labels))

        return replace(annotation, types=types)

    def _update_label(
        self,
        label: AnnotationLabel,
        type_id: int,
        nodes: dict[int, float],
        node_id: int,
        node_time: float,
    ) -> list[AnnotationLabel]:
        start, end = nodes[label.s_node], nodes[label.e_node]

        if start > node_time or end < node_time:
            return [label]
        if start == node_time or end == node_time:
            raise ValueError("Node already exists at this exact time")

        labels = []

        left_label = replace(label, e_node=node_id)
        self.annotation_repository.update_label(left_label)

        right_label = self.annotation_repository.create_label(
            AnnotationLabel(s_node=node_id, e_node=label.e_node),
            type_id,
        )

        labels.extend((left_label, right_label))

        return [left_label, right_label]
