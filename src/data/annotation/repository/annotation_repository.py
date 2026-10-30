from core.annotation.entity.annotation import Annotation
from core.annotation.repository.annotation_repository import AnnotationRepository
from data.annotation.datasource.annotation_datasource import AnnotationDataSource
from data.annotation.entity.annotation import AnnotationEntity
from data.annotation.entity.annotation_node import AnnotationNodeEntity
from data.annotation.mapping.annotation_mapping import (
    annotation_to_entity,
    entity_to_annotation,
)


class AnnotationRepositoryImpl(AnnotationRepository):
    def __init__(self, local_datasource: AnnotationDataSource):
        self.local_datasource = local_datasource

    def save_annotation(self, annotation: Annotation, filename: str) -> Annotation:
        entity = annotation_to_entity(annotation, filename)
        entity = self.local_datasource.save_annotation(entity)
        return entity_to_annotation(entity)

    def create_annotation(self, filename: str) -> int:
        entity = self.local_datasource.get_annotation_by_filename(filename)
        if entity is not None:
            # raise ValueError(
            #     "Annotation for this file already exists in project database"
            # )
            return entity.id

        entity = self.local_datasource.save_annotation(
            AnnotationEntity(file_name=filename)
        )

        return entity.id

    def create_nodes(self, annotation_id: int, nodes: list[float]) -> dict[int, float]:
        node_entities = [
            AnnotationNodeEntity(annotation_id=annotation_id, time=time)
            for time in nodes
        ]
        node_entities = self.local_datasource.save_nodes(node_entities)
        return {node.id: node.time for node in node_entities}
