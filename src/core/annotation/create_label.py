from dataclasses import replace

from core.annotation.create_node import create_node
from core.annotation.delete_interval import delete_annotation_interval
from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
)
from core.base.use_case_sync import UseCaseSync


class CreateLabel(UseCaseSync[Annotation]):
    def __init__(self, annotation: Annotation, type: int, start: float, end: float):
        super().__init__()
        self.annotation = annotation
        self.type = type
        self.start = start
        self.end = end

    def invoke(self) -> Annotation:
        annotation, s_node = create_node(self.annotation, self.start)
        annotation, e_node = create_node(annotation, self.end)

        annotation = delete_annotation_interval(annotation, [self.type], s_node, e_node)

        type_labels = annotation.types[self.type].labels.copy()
        if len(type_labels) == 0:
            new_label_idx = 0
        else:
            new_label_idx = max([label.id for label in type_labels]) + 1

        type_labels.append(AnnotationLabel(new_label_idx, s_node, e_node))
        new_type = replace(annotation.types[self.type], labels=type_labels)

        return replace(
            annotation,
            types=self.annotation.types[: self.type]
            + [new_type]
            + self.annotation.types[self.type + 1 :],
        )
