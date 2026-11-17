from sqlalchemy import Row

from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
)
from core.annotation.entity.recording import Recording
from core.annotation.entity.tier_label import TierLabel
from data.annotation.entity.annotation import AnnotationEntity
from data.annotation.entity.annotation_label import AnnotationLabelEntity
from data.annotation.entity.annotation_type import AnnotationTypeEntity
from data.annotation.entity.recording_channel import RecordingChannelEntity


def entity_to_annotation(entity: AnnotationEntity) -> Annotation:
    return Annotation(
        {node_entity.id: node_entity.time for node_entity in entity.nodes},
        [entity_to_type(type_entity) for type_entity in entity.types],
        entity.id,
    )


def entity_to_type(entity: AnnotationTypeEntity) -> AnnotationType:
    return AnnotationType(
        entity.name, [entity_to_label(label) for label in entity.labels], entity.id
    )


def entity_to_label(entity: AnnotationLabelEntity) -> AnnotationLabel:
    return AnnotationLabel(
        entity.start_node_id, entity.end_node_id, entity.label_text, entity.id
    )


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


def row_to_tier_label(row: Row) -> TierLabel:
    file_stem, tier_name, id, text, s_node, e_node, start, end = row
    return TierLabel(
        file_stem, tier_name, AnnotationLabel(s_node, e_node, text, id), start, end
    )


def entity_to_recording(
    entity: AnnotationEntity, channels: list[RecordingChannelEntity]
) -> Recording:
    """The recording an annotation row describes, given its channel rows. The links
    to talkers have to be loaded"""
    return Recording(
        file_stem=entity.file_stem,
        audio_file=entity.audio_file,
        annotation_file=entity.annotation_file,
        channel_files={row.channel: row.audio_file for row in channels},
        channel_talkers={
            row.channel: row.talker.name for row in channels if row.talker is not None
        },
        data_files=dict(entity.data_files or {}),
        talkers=[link.talker.name for link in entity.talker_links],
        fields=dict(entity.fields or {}),
    )


def set_recording_columns(entity: AnnotationEntity, recording: Recording):
    entity.audio_file = recording.audio_file
    entity.annotation_file = recording.annotation_file
    entity.data_files = dict(recording.data_files)
    entity.fields = dict(recording.fields)
