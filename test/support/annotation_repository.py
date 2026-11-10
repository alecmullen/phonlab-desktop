from dataclasses import replace

from core.annotation.entity.annotation import Annotation
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)


class SeedableAnnotationRepository(InMemAnnotationRepository):
    """In-memory repository that can be pre-populated with an annotation whose ids
    are already set, so tests can name node/label/type ids by position"""

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
            for label in self.types[id][-1].labels:
                if label.id is not None:
                    self._next_label_id = max(self._next_label_id, label.id + 1)
        return self.get_annotation_by_id(id)
