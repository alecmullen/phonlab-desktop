from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
)
from data.annotation.entity.annotation import AnnotationEntity
from data.annotation.entity.annotation_label import AnnotationLabelEntity
from data.annotation.entity.annotation_node import AnnotationNodeEntity
from data.annotation.entity.annotation_type import AnnotationTypeEntity


def entity_to_annotation(entity: AnnotationEntity) -> Annotation:
    return Annotation(
        {node_entity.id: node_entity.time for node_entity in entity.nodes},
        [entity_to_type(type_entity) for type_entity in entity.types],
    )


def entity_to_type(entity: AnnotationTypeEntity) -> AnnotationType:
    return AnnotationType(
        entity.name, [entity_to_label(label) for label in entity.labels]
    )


def entity_to_label(entity: AnnotationLabelEntity) -> AnnotationLabel:
    return AnnotationLabel(
        entity.start_node_id, entity.end_node_id, entity.label_text, entity.id
    )


def annotation_to_entity(annotation: Annotation, filename: str) -> AnnotationEntity:
    entity = AnnotationEntity(
        file_name=filename,
        nodes=[
            AnnotationNodeEntity(id=id, time=time)
            for id, time in annotation.nodes.items()
        ],
        types=[type_to_entity(type) for type in annotation.types],
    )

    if annotation.id is not None:
        entity.id = annotation.id
    return entity


def type_to_entity(type: AnnotationType) -> AnnotationTypeEntity:
    entity = AnnotationTypeEntity(
        name=type.type, labels=[label_to_entity(label) for label in type.labels]
    )
    if type.id is not None:
        entity.id = type.id
    return entity


def label_to_entity(label: AnnotationLabel) -> AnnotationLabelEntity:
    entity = AnnotationLabelEntity(
        start_node_id=label.s_node, end_node_id=label.e_node, label_text=label.label
    )
    if label.id is not None:
        entity.id = label.id
    return entity
