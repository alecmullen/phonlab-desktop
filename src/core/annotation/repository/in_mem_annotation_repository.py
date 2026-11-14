from dataclasses import replace

from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
    get_matching_node,
)
from core.annotation.repository.annotation_repository import AnnotationRepository


class InMemAnnotationRepository(AnnotationRepository):
    """In-memory repository that assigns ids like the database does: type and label
    ids are unique across the whole repository (counting from 0). Also used for
    in-memory annotation editing when no database is connected"""

    def __init__(self):
        self.filenames: dict[int, str] = {}
        self.nodes: dict[int, dict[int, float]] = {}
        self.types: dict[int, list[AnnotationType]] = {}
        self._next_type_id = 0
        self._next_label_id = 0

    def create_annotation(self, file_stem: str) -> int:
        if file_stem in self.filenames.values():
            raise ValueError(
                "Annotation for this file already exists in project database"
            )
        id = len(self.filenames)
        self.filenames[id] = file_stem
        self.nodes[id] = {}
        self.types[id] = []
        return id

    def clear_annotation(self, annotation_id: int) -> None:
        self.nodes[annotation_id] = {}
        self.types[annotation_id] = []

    def create_node(
        self, annotation_id: int, time: float, same_threshold: float
    ) -> tuple[int, float]:
        existing = self.nodes[annotation_id]
        node_ids, node_times = zip(*sorted(existing.items(), key=lambda item: item[1]))

        match = get_matching_node(
            list(node_times), time, same_threshold, list(node_ids)
        )
        if match is not None:
            return match, existing[match]
        node_id = max(existing, default=-1) + 1
        existing[node_id] = time
        return node_id, time

    def create_nodes(
        self, annotation_id: int, nodes: list[float], same_threshold: float
    ) -> dict[int, float]:
        created: dict[int, float] = {}

        existing = self.nodes[annotation_id]
        if len(existing) > 0:
            node_ids, node_times = zip(
                *sorted(existing.items(), key=lambda item: item[1])
            )
        else:
            node_ids, node_times = (), ()

        for time in nodes:
            match = get_matching_node(
                list(node_times), time, same_threshold, list(node_ids)
            )
            if match is None:
                node_id = max(existing, default=-1) + 1
                existing[node_id] = time
            else:
                node_id, time = match, existing[match]
            created[node_id] = time
        return created

    def create_types(self, annotation_id: int, types: list[AnnotationType]):
        for type in types:
            labels = []
            for label in type.labels:
                labels.append(replace(label, id=self._next_label_id))
                self._next_label_id += 1
            self.types[annotation_id].append(
                replace(type, labels=labels, id=self._next_type_id)
            )
            self._next_type_id += 1

    def get_annotation_by_id(self, id: int) -> Annotation:
        if id not in self.filenames:
            raise ValueError("Annotation with that id does not exist in database")
        return Annotation(dict(self.nodes[id]), list(self.types[id]), id)

    def find_annotation_by_file_stem(self, file_stem: str) -> Annotation | None:
        for id, stem in self.filenames.items():
            if stem == file_stem:
                return self.get_annotation_by_id(id)
        return None

    def _find_type(self, type_id: int) -> tuple[int, int]:
        for annotation_id, types in self.types.items():
            for idx, type in enumerate(types):
                if type.id == type_id:
                    return annotation_id, idx
        raise ValueError("Type does not exist in database")

    def _set_labels(self, type_id: int, labels: list[AnnotationLabel]):
        annotation_id, idx = self._find_type(type_id)
        self.types[annotation_id][idx] = replace(
            self.types[annotation_id][idx], labels=labels
        )

    def _labels(self, type_id: int) -> list[AnnotationLabel]:
        annotation_id, idx = self._find_type(type_id)
        return list(self.types[annotation_id][idx].labels)

    def create_label(self, label: AnnotationLabel, type_id: int) -> AnnotationLabel:
        labels = self._labels(type_id)
        created = replace(label, id=self._next_label_id)
        self._next_label_id += 1
        self._set_labels(type_id, [*labels, created])
        return created

    def delete_node(self, node_id: int):
        for nodes in self.nodes.values():
            nodes.pop(node_id, None)

    def update_label(self, label: AnnotationLabel):
        for annotation_id, types in self.types.items():
            for idx, type in enumerate(types):
                if any(l.id == label.id for l in type.labels):
                    self.types[annotation_id][idx] = replace(
                        type,
                        labels=[label if l.id == label.id else l for l in type.labels],
                    )
                    return

    def update_node(self, node_id: int, time: float):
        for nodes in self.nodes.values():
            if node_id in nodes:
                nodes[node_id] = time

    def delete_nodes_if_no_labels(self, ids: list[int]) -> list[int]:
        deleted = []
        for id in set(ids):
            used = any(
                id in (l.s_node, l.e_node)
                for types in self.types.values()
                for type in types
                for l in type.labels
            )
            if not used:
                self.delete_node(id)
                deleted.append(id)
        return deleted

    def delete_label(self, label: AnnotationLabel):
        for annotation_id, types in self.types.items():
            for idx, type in enumerate(types):
                if any(l.id == label.id for l in type.labels):
                    self.types[annotation_id][idx] = replace(
                        type, labels=[l for l in type.labels if l.id != label.id]
                    )
                    return
