from dataclasses import replace

from core.annotation.entity.annotation import Annotation, AnnotationLabel
from core.base.use_case_sync import UseCaseSync


class DeleteEndNodeError(ValueError):
    pass


class DeleteNode(UseCaseSync[Annotation]):
    def __init__(self, annotation: Annotation, node: int):
        super().__init__()
        self.annotation = annotation
        self.node = node

    def invoke(self) -> Annotation:
        if self.node not in self.annotation.nodes:
            raise ValueError("Can't find node to delete")

        types = []
        for type in self.annotation.types:
            labels = self._labels_without_node(self.node, type.labels)
            types.append(replace(type, labels=labels))

        nodes = {
            key: value
            for key, value in self.annotation.nodes.items()
            if key != self.node
        }
        return Annotation(nodes=nodes, types=types)

    def _labels_without_node(
        self, node: int, labels: list[AnnotationLabel]
    ) -> list[AnnotationLabel]:
        """Returns the tier's labels with `node` removed, or None if the node is
        an end node of the tier with an interval label attached."""
        before = [
            label for label in labels if label.e_node == node and label.s_node != node
        ]
        after = [
            label for label in labels if label.s_node == node and label.e_node != node
        ]

        if len(before) == len(after) == 1:
            replacements = {
                before[0].id: replace(
                    before[0],
                    e_node=after[0].e_node,
                    label=before[0].label + after[0].label,
                )
            }
        else:
            tier_nodes = sorted(
                {n for label in labels for n in (label.s_node, label.e_node)},
                key=lambda n: (self.annotation.nodes[n], n),
            )
            if node not in tier_nodes:
                return list(labels)

            node_idx = tier_nodes.index(node)
            before_node = tier_nodes[node_idx - 1] if node_idx > 0 else None
            after_node = (
                tier_nodes[node_idx + 1] if node_idx < len(tier_nodes) - 1 else None
            )

            if (before and after_node is None) or (after and before_node is None):
                raise DeleteEndNodeError()

            replacements = {
                label.id: replace(label, e_node=after_node) for label in before
            } | {label.id: replace(label, s_node=before_node) for label in after}

        return [
            replacements.get(label.id, label)
            for label in labels
            if label.id in replacements or node not in (label.s_node, label.e_node)
        ]
