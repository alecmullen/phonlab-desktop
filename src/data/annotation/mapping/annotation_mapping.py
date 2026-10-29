from core.annotation.entity.annotation import Annotation, AnnotationLabel
from data.annotation.entity.annotation import AnnotationEntity
from data.annotation.entity.annotation_label import AnnotationLabelEntity
from data.annotation.entity.annotation_node import AnnotationNodeEntity


def entity_to_annotation(entity: AnnotationEntity) -> Annotation:
    return Annotation(
        {node_entity.id: node_entity.time for node_entity in entity.nodes},
        [entity_to_label(label_entity) for label_entity in entity.labels], #TODO: map types
    )


def entity_to_label(entity: AnnotationLabelEntity) -> AnnotationLabel:
    return AnnotationLabel(
        entity.id, entity.start_node_id, entity.end_node_id, entity.label_text
    )


def annotation_to_entity(annotation: Annotation) -> AnnotationEntity:
    return AnnotationEntity(
        nodes=[AnnotationNodeEntity(id=id, time=time) for id, time in annotation.nodes.items()],
        labels=[AnnotationLabelEntity() for label in annotation.labels]
    )
