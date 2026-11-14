from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
)
from core.annotation.repository.annotation_repository import AnnotationRepository
from data.annotation.datasource.annotation_datasource import AnnotationDataSource
from data.annotation.entity.annotation import AnnotationEntity
from data.annotation.entity.annotation_node import AnnotationNodeEntity
from data.annotation.mapping.annotation_mapping import (
    entity_to_annotation,
    entity_to_label,
    label_to_entity,
    type_to_entity,
)


class DataAnnotationRepository(AnnotationRepository):
    def __init__(self, local_datasource: AnnotationDataSource):
        self.local_datasource = local_datasource

    def create_annotation(self, file_stem: str) -> int:
        entity = self.local_datasource.find_annotation_by_file_stem(file_stem)
        if entity is not None:
            raise ValueError(
                "Annotation for this file already exists in project database"
            )

        return self.local_datasource.add_annotation(
            AnnotationEntity(file_stem=file_stem)
        )

    def create_annotations_if_missing(self, file_stems: list[str]) -> None:
        self.local_datasource.add_annotations_if_missing(file_stems)

    def reset(self) -> str | None:
        return self.local_datasource.reset()

    def clear_annotation(self, annotation_id: int) -> None:
        self.local_datasource.clear_annotation(annotation_id)

    def get_annotation_by_id(self, id: int) -> Annotation:
        entity = self.local_datasource.get_annotation_by_id(id)
        return entity_to_annotation(entity)

    def find_annotation_by_file_stem(self, file_stem: str) -> Annotation | None:
        entity = self.local_datasource.find_annotation_by_file_stem(file_stem)
        if entity is not None:
            return entity_to_annotation(entity)
        else:
            return None

    def create_node(
        self, annotation_id: int, time: float, same_threshold: float = 0.0
    ) -> tuple[int, float]:
        node = self.local_datasource.find_node_by_time(
            annotation_id, time, same_threshold
        )
        if node is None:
            node = self.local_datasource.add_node(
                AnnotationNodeEntity(annotation_id=annotation_id, time=time)
            )
        return (node.id, node.time)

    def create_nodes(
        self, annotation_id: int, nodes: list[float], same_threshold: float = 0.0
    ) -> dict[int, float]:
        node_entities = []
        for time in nodes:
            node_entity = self.local_datasource.find_node_by_time(
                annotation_id, time, same_threshold
            )
            if node_entity is None:
                node_entity = AnnotationNodeEntity(
                    annotation_id=annotation_id, time=time
                )
            node_entities.append(node_entity)

        node_entities = self.local_datasource.add_nodes(node_entities)
        return {node.id: node.time for node in node_entities}

    def update_node(self, node_id: int, time: float):
        self.local_datasource.update_node(AnnotationNodeEntity(id=node_id, time=time))

    def delete_node(self, node_id: int):
        self.local_datasource.delete_node(node_id)

    def delete_nodes_if_no_labels(self, ids: list[int]) -> list[int]:
        return self.local_datasource.delete_nodes_if_no_labels(ids)

    def create_types(self, annotation_id: int, types: list[AnnotationType]):
        type_entities = [type_to_entity(type) for type in types]
        for entity in type_entities:
            entity.annotation_id = annotation_id
        self.local_datasource.add_types(type_entities)

    def create_label(self, label: AnnotationLabel, type_id: int) -> AnnotationLabel:
        entity = label_to_entity(label)
        entity.annotation_type_id = type_id
        entity = self.local_datasource.add_label(entity)
        return entity_to_label(entity)

    def update_label(self, label: AnnotationLabel):
        entity = label_to_entity(label)
        self.local_datasource.merge_label(entity)

    def delete_label(self, label: AnnotationLabel):
        entity = label_to_entity(label)
        self.local_datasource.delete_label(entity)
