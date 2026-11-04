from dataclasses import replace

from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
    get_matching_node,
)
from core.annotation.repository.annotation_repository import AnnotationRepository


class FakeAnnotationRepository(AnnotationRepository):
    """In-memory repository that assigns ids like the database does, but counting
    from 0 (labels per type) so tests can name ids by position"""

    def __init__(self):
        self.filenames: dict[int, str] = {}
        self.nodes: dict[int, dict[int, float]] = {}
        self.types: dict[int, list[AnnotationType]] = {}
        self._next_type_id = 0

    def seed(self, annotation: Annotation) -> Annotation:
        """Stores an annotation as-is (ids included) and returns it with its id"""
        id = len(self.filenames)
        self.filenames[id] = f"seeded{id}"
        self.nodes[id] = dict(annotation.nodes)
        self.types[id] = []
        for idx, type in enumerate(annotation.types):
            type_id = type.id if type.id is not None else idx
            self.types[id].append(replace(type, id=type_id, labels=list(type.labels)))
            self._next_type_id = max(self._next_type_id, type_id + 1)
        return self.get_annotation_by_id(id)

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

    def create_node(
        self, annotation_id: int, time: float, same_threshold: float
    ) -> tuple[int, float]:
        existing = self.nodes[annotation_id]
        match = get_matching_node(existing, time, same_threshold)
        if match is not None:
            return match, existing[match]
        node_id = max(existing, default=-1) + 1
        existing[node_id] = time
        return node_id, time

    def create_nodes(
        self, annotation_id: int, nodes: list[float], same_threshold: float
    ) -> dict[int, float]:
        created: dict[int, float] = {}
        for time in nodes:
            node_id, node_time = self.create_node(annotation_id, time, same_threshold)
            created[node_id] = node_time
        return created

    def create_types(self, annotation_id: int, types: list[AnnotationType]):
        for type in types:
            labels = [replace(label, id=idx) for idx, label in enumerate(type.labels)]
            self.types[annotation_id].append(
                replace(type, labels=labels, id=self._next_type_id)
            )
            self._next_type_id += 1

    def get_annotation_by_id(self, id: int) -> Annotation:
        if id not in self.filenames:
            raise ValueError("Annotation with that id does not exist in database")
        return Annotation(dict(self.nodes[id]), list(self.types[id]), id)

    def get_annotation_by_file_stem(self, file_stem: str) -> Annotation | None:
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

    def create_label(self, label: AnnotationLabel, type_id: int):
        labels = self._labels(type_id)
        next_id = max((l.id for l in labels if l.id is not None), default=-1) + 1
        self._set_labels(type_id, [*labels, replace(label, id=next_id)])

    def update_label(self, label: AnnotationLabel, type_id: int):
        self._set_labels(
            type_id, [label if l.id == label.id else l for l in self._labels(type_id)]
        )

    def delete_label(self, label: AnnotationLabel):
        for annotation_id, types in self.types.items():
            for idx, type in enumerate(types):
                if any(l.id == label.id for l in type.labels):
                    self.types[annotation_id][idx] = replace(
                        type, labels=[l for l in type.labels if l.id != label.id]
                    )
                    return
