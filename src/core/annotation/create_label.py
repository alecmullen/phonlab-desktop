from dataclasses import replace

from core.annotation.create_node import create_node
from core.annotation.delete_interval import delete_annotation_interval
from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
)
from core.base.use_case_sync import UseCaseSync


class ZeroLengthLabelError(ValueError):
    pass


class CreateLabel(UseCaseSync[Annotation]):
    def __call__(
        self,
        annotation: Annotation,
        type: int,
        start: float,
        end: float,
        same_node_threshold: float | None = None,
    ) -> Annotation:
        annotation, s_node = create_node(annotation, start, same_node_threshold)
        annotation, e_node = create_node(annotation, end, same_node_threshold)

        if s_node == e_node:
            raise ZeroLengthLabelError()

        annotation = delete_annotation_interval(annotation, [type], s_node, e_node)

        type_labels = annotation.types[type].labels.copy()

        type_labels.append(AnnotationLabel(s_node, e_node))
        new_type = replace(annotation.types[type], labels=type_labels)

        return replace(
            annotation,
            types=annotation.types[:type] + [new_type] + annotation.types[type + 1 :],
        )
