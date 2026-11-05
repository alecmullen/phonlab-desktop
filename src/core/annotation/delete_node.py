from dataclasses import replace

from core.annotation.entity.annotation import (
    Annotation,
    AnnotationType,
)
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync


class DeleteNodeError(ValueError):
    pass


class DeleteNode(UseCaseSync[Annotation]):
    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(self, annotation: Annotation, node: int) -> Annotation:
        if node not in annotation.nodes:
            raise ValueError("Can't find node to delete")

        types = []
        for type in annotation.types:
            types.append(self._remove_node_from_type_labels(node, type))

        self.annotation_repository.delete_node(node)
        nodes = {key: value for key, value in annotation.nodes.items() if key != node}
        return Annotation(nodes=nodes, types=types)

    def _remove_node_from_type_labels(
        self, node: int, type: AnnotationType
    ) -> AnnotationType:
        """Returns the tier's labels with `node` removed. Merges labels if there is one before
        the node and one after. Point labels are deleted. Raises error if attached labels
        are asymmetrical or exceed 1 per side"""
        before = [
            label
            for label in type.labels
            if label.e_node == node and label.s_node != node
        ]
        after = [
            label
            for label in type.labels
            if label.s_node == node and label.e_node != node
        ]

        if len(before) == len(after) == 1:
            replacements = {
                before[0].id: replace(
                    before[0],
                    e_node=after[0].e_node,
                    label=before[0].label + after[0].label,
                )
            }
        elif len(before) == len(after) == 0:
            replacements = {}
        else:
            raise DeleteNodeError(
                "Operation only defined for nodes with no connected intervals, or exactly one interval connected on each side."
            )

        updated_labels = []
        for label in type.labels:
            if label.id in replacements:
                self.annotation_repository.update_label(
                    replacements[label.id], type.get_id()
                )
                updated_labels.append(replacements[label.id])
            elif node in (label.s_node, label.e_node):
                self.annotation_repository.delete_label(label)
            else:
                updated_labels.append(label)

        return replace(type, labels=updated_labels)
