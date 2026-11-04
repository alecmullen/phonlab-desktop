from dataclasses import replace

from core.annotation.entity.annotation import Annotation, AnnotationLabel
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync


class ClearInterval(UseCaseSync):
    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(
        self,
        annotation: Annotation,
        type_ids: list[int],
        s_node_interval: int,
        e_node_interval: int,
    ):
        nodes = annotation.nodes

        types = (type for type in annotation.types if type.id in type_ids)
        for type in types:
            for label in type.labels:
                if (
                    nodes[label.e_node] <= nodes[e_node_interval]
                    and nodes[label.s_node] >= nodes[s_node_interval]
                ):
                    # Interval contains entire label
                    self.annotation_repository.delete_label(label)
                    continue

                split = False
                if (
                    nodes[label.e_node] > nodes[s_node_interval]
                    and nodes[label.s_node] < nodes[s_node_interval]
                ):
                    # Overlaps interval, not including start of label
                    self.annotation_repository.update_label(
                        replace(label, e_node=s_node_interval), type.get_id()
                    )
                    split = True
                if (
                    nodes[label.e_node] > nodes[e_node_interval]
                    and nodes[label.s_node] < nodes[e_node_interval]
                ):
                    # Overlaps interval, not including end of label
                    if split:
                        self.annotation_repository.create_label(
                            AnnotationLabel(
                                s_node=e_node_interval, e_node=label.e_node
                            ),
                            type.get_id(),
                        )
                    else:
                        self.annotation_repository.update_label(
                            replace(label, s_node=e_node_interval), type.get_id()
                        )
