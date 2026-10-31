from dataclasses import replace

from core.annotation.entity.annotation import (
    Annotation,
    AnnotationType,
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

    def create_annotation(self, filename: str) -> int:
        if filename in self.filenames.values():
            raise ValueError(
                "Annotation for this file already exists in project database"
            )
        id = len(self.filenames)
        self.filenames[id] = filename
        self.nodes[id] = {}
        self.types[id] = []
        return id

    def create_nodes(self, annotation_id: int, nodes: list[float]) -> dict[int, float]:
        existing = self.nodes[annotation_id]
        created = {len(existing) + idx: time for idx, time in enumerate(nodes)}
        existing.update(created)
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
        return Annotation(self.nodes[id], self.types[id], id)
