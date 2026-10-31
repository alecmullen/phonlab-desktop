from core.annotation.entity.annotation import Annotation, AnnotationType
from core.annotation.repository.annotation_repository import AnnotationRepository
from data.annotation.datasource.annotation_datasource import AnnotationDataSource
from data.annotation.entity.annotation import AnnotationEntity
from data.annotation.entity.annotation_node import AnnotationNodeEntity
from data.annotation.mapping.annotation_mapping import (
    entity_to_annotation,
    type_to_entity,
)


class AnnotationRepositoryImpl(AnnotationRepository):
    def __init__(self, local_datasource: AnnotationDataSource):
        self.local_datasource = local_datasource

    def create_annotation(self, filename: str) -> int:
        entity = self.local_datasource.find_annotation_by_filename(filename)
        if entity is not None:
            raise ValueError(
                "Annotation for this file already exists in project database"
            )

        return self.local_datasource.add_annotation(
            AnnotationEntity(file_name=filename)
        )

    def get_annotation_by_id(self, id: int) -> Annotation:
        entity = self.local_datasource.get_annotation_by_id(id)
        return entity_to_annotation(entity)

    def create_nodes(self, annotation_id: int, nodes: list[float]) -> dict[int, float]:
        node_entities = [
            AnnotationNodeEntity(annotation_id=annotation_id, time=time)
            for time in nodes
        ]
        node_entities = self.local_datasource.add_nodes(node_entities)
        return {node.id: node.time for node in node_entities}

    def create_types(self, annotation_id: int, types: list[AnnotationType]):
        type_entities = [type_to_entity(type) for type in types]
        for entity in type_entities:
            entity.annotation_id = annotation_id
        self.local_datasource.add_types(type_entities)
