import bisect
from typing import Any

from core.annotation.entity.annotation import (
    Annotation,
    AnnotationLabel,
    AnnotationType,
)
from core.annotation.entity.metadata import MetadataColumn, MetadataTarget
from core.annotation.entity.recording import Recording, RecordingUpsertResult
from core.annotation.entity.tier_label import TierLabel
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.inspect_database.entity.table_data import TableData
from data.annotation.datasource.annotation_datasource import AnnotationDataSource
from data.annotation.entity.annotation import AnnotationEntity
from data.annotation.entity.annotation_node import AnnotationNodeEntity
from data.annotation.mapping.annotation_mapping import (
    entity_to_annotation,
    entity_to_label,
    entity_to_recording,
    label_to_entity,
    row_to_tier_label,
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

    def close(self) -> None:
        self.local_datasource.close()

    def clear_annotation(self, annotation_id: int) -> None:
        self.local_datasource.clear_annotation(annotation_id)

    def get_annotation_by_id(self, id: int) -> Annotation:
        entity = self.local_datasource.get_annotation_by_id(id)
        return entity_to_annotation(entity)

    def list_tier_names(self) -> list[str]:
        return self.local_datasource.list_tier_names()

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
        # A time that is within the threshold of a node the annotation already has
        # is that node. The nodes are read once, not looked up for every time.
        existing = self.local_datasource.list_nodes(annotation_id)
        existing_times = [node.time for node in existing]

        node_entities = []
        for time in nodes:
            node_entity = None
            idx = bisect.bisect_left(existing_times, time - same_threshold)
            if idx < len(existing) and existing_times[idx] <= time + same_threshold:
                node_entity = existing[idx]
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

    def find_labels_by_tier_name(
        self, tier_name: str, file_stem: str | None = None
    ) -> list[TierLabel]:
        rows = self.local_datasource.find_labels_by_tier_name(tier_name, file_stem)
        return [row_to_tier_label(row) for row in rows]

    def upsert_recordings(
        self, recordings: list[Recording], remove_others: bool = True
    ) -> RecordingUpsertResult:
        return self.local_datasource.upsert_recordings(recordings, remove_others)

    def list_recordings(self) -> list[Recording]:
        channels = self.local_datasource.list_channels()
        return [
            entity_to_recording(entity, channels.get(entity.id, []))
            for entity in self.local_datasource.list_recordings()
        ]

    def list_talkers(self) -> list[str]:
        return self.local_datasource.list_talkers()

    def builtin_columns(self, target: MetadataTarget) -> list[str]:
        return self.local_datasource.builtin_columns(target)

    def add_metadata(
        self,
        target: MetadataTarget,
        columns: list[MetadataColumn],
        values: dict[str, dict[str, Any]],
    ) -> int:
        return self.local_datasource.add_metadata(target, columns, values)

    def read_metadata(self, target: MetadataTarget) -> dict[str, dict[str, Any]]:
        return self.local_datasource.read_metadata(target)

    def tier_label_counts(self, tier_name: str) -> dict[str, int]:
        return self.local_datasource.tier_label_counts(tier_name)

    def replace_words(
        self, columns: list[MetadataColumn], rows: list[tuple[str, dict[str, Any]]]
    ) -> int:
        return self.local_datasource.replace_words(columns, rows)

    def list_tables(self) -> list[str]:
        return self.local_datasource.list_tables()

    def read_table(self, name: str, limit: int) -> TableData:
        return self.local_datasource.read_table(name, limit)
