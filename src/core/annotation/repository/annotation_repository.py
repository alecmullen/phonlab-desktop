from typing import Protocol

from core.annotation.entity.annotation import Annotation


class AnnotationRepository(Protocol):
    def save_annotation(self, annotation: Annotation, filename: str) -> Annotation: ...
    def create_annotation(self, filename: str) -> int: ...
    def create_nodes(
        self, annotation_id: int, nodes: list[float]
    ) -> dict[int, float]: ...
