from typing import Protocol

from core.annotation.entity.annotation import Annotation


class AnnotationRepository(Protocol):
    def save_annotation(self, annotation: Annotation): ...
