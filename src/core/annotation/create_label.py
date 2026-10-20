from dataclasses import replace

from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    get_matching_node,
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
        nodes = self.annotation.nodes.copy()
        if len(nodes) == 0:
            new_node_idx = 0
        else:
            new_node_idx = max([node for node in nodes]) + 1

        s_node = get_matching_node(nodes, self.start)
        if s_node is None:
            nodes[new_node_idx] = self.start
            s_node = new_node_idx
            new_node_idx += 1

        e_node = get_matching_node(nodes, self.end)
        if e_node is None:
            nodes[new_node_idx] = self.end
            e_node = new_node_idx

        type_labels = self.annotation.types[self.type].labels.copy()
        if len(type_labels) == 0:
            new_label_idx = 0
        else:
            new_label_idx = max([label.id for label in type_labels]) + 1

        type_labels.append(AnnotationLabel(new_label_idx, s_node, e_node))
        new_type = replace(self.annotation.types[self.type], labels=type_labels)

        return replace(
            self.annotation,
            nodes=nodes,
            types=self.annotation.types[: self.type]
            + [new_type]
            + self.annotation.types[self.type + 1 :],
        )
