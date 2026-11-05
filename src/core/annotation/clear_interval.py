from dataclasses import replace

from core.annotation.entity.annotation import Annotation, AnnotationLabel
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync


class ClearInterval(UseCaseSync[Annotation]):
    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(
        self,
        annotation: Annotation,
        type_ids: list[int],
        s_node_interval: int,
        e_node_interval: int,
    ) -> Annotation:
        nodes = annotation.nodes

        types = []
        for type in annotation.types:
            if not type.id in type_ids:
                types.append(type)
                continue

            labels = []
            deleted_nodes = set()
            for label in type.labels:
                updated_labels, deleted_ids = self._update_label(
                    label, type.get_id(), nodes, s_node_interval, e_node_interval
                )
                labels.extend(updated_labels)
                deleted_nodes.update(deleted_ids)

            types.append(replace(type, labels=labels))

        return replace(
            annotation,
            types=types,
            nodes={
                id: time
                for id, time in annotation.nodes.items()
                if id not in deleted_nodes
            },
        )

    def _update_label(
        self,
        label: AnnotationLabel,
        type_id: int,
        nodes: dict[int, float],
        s_node_interval: int,
        e_node_interval: int,
    ) -> tuple[list[AnnotationLabel], list[int]]:
        label_range = self._nodes_to_tuple_range(nodes, label.s_node, label.e_node)
        interval_range = self._nodes_to_tuple_range(
            nodes, s_node_interval, e_node_interval
        )

        if self._label_outside_interval(label_range, interval_range):
            return [label], []

        potential_node_orphans = []
        labels = []
        split = False
        if self._label_inside_interval(label_range, interval_range):
            self.annotation_repository.delete_label(label)
            potential_node_orphans.extend((label.s_node, label.e_node))

        else:
            if self._label_starts_before_interval(label_range, interval_range):
                new_label = replace(label, e_node=s_node_interval)
                self.annotation_repository.update_label(new_label)

                potential_node_orphans.append(label.e_node)

                labels.append(new_label)
                split = True

            if self._label_ends_after_interval(label_range, interval_range):
                if split:
                    new_label = self.annotation_repository.create_label(
                        AnnotationLabel(s_node=e_node_interval, e_node=label.e_node),
                        type_id,
                    )
                else:
                    new_label = replace(label, s_node=e_node_interval)
                    self.annotation_repository.update_label(new_label)

                    potential_node_orphans.append(label.s_node)

                labels.append(new_label)

        deleted_ids = self.annotation_repository.delete_nodes_if_no_labels(
            potential_node_orphans
        )

        return labels, deleted_ids

    def _nodes_to_tuple_range(
        self, nodes: dict[int, float], s_node: int, e_node: int
    ) -> tuple[float, float]:
        return (nodes[s_node], nodes[e_node])

    def _label_outside_interval(
        self, label: tuple[float, float], interval: tuple[float, float]
    ) -> bool:
        return label[1] <= interval[0] or label[0] >= interval[1]

    def _label_inside_interval(
        self, label: tuple[float, float], interval: tuple[float, float]
    ) -> bool:
        return label[1] <= interval[1] and label[0] >= interval[0]

    def _label_starts_before_interval(
        self, label: tuple[float, float], interval: tuple[float, float]
    ) -> bool:
        return label[0] < interval[0]

    def _label_ends_after_interval(
        self, label: tuple[float, float], interval: tuple[float, float]
    ) -> bool:
        return label[1] > interval[1]
