from sqlalchemy import exists, or_, select
from sqlalchemy.orm import joinedload

from data.annotation.entity.annotation import AnnotationEntity
from data.annotation.entity.annotation_label import AnnotationLabelEntity
from data.annotation.entity.annotation_node import AnnotationNodeEntity
from data.annotation.entity.annotation_type import AnnotationTypeEntity
from data.base.datasource import DataSource


class AnnotationDataSource(DataSource):
    def find_annotation_by_file_stem(self, file_stem: str) -> AnnotationEntity | None:
        with self.database.open_session() as session:
            stmt = (
                select(AnnotationEntity)
                .where(AnnotationEntity.file_stem == file_stem)
                .options(
                    joinedload(AnnotationEntity.nodes),
                    joinedload(AnnotationEntity.types).subqueryload(
                        AnnotationTypeEntity.labels
                    ),
                )
            )
            annotation = session.scalar(stmt)

        return annotation

    def get_annotation_by_id(self, id: int) -> AnnotationEntity:
        with self.database.open_session() as session:
            stmt = (
                select(AnnotationEntity)
                .where(AnnotationEntity.id == id)
                .options(
                    joinedload(AnnotationEntity.nodes),
                    joinedload(AnnotationEntity.types).subqueryload(
                        AnnotationTypeEntity.labels
                    ),
                )
            )
            annotation = session.scalar(stmt)

        if annotation is None:
            raise ValueError("Annotation with that id does not exist in database")

        return annotation

    def add_annotation(self, annotation: AnnotationEntity) -> int:
        with self.database.open_session() as session:
            session.add(annotation)
            session.flush()
            id = annotation.id
            session.commit()

        return id

    def find_node_by_time(
        self, annotation_id: int, time: float, threshold: float
    ) -> AnnotationNodeEntity | None:
        with self.database.open_session() as session:
            stmt = (
                select(AnnotationNodeEntity)
                .where(AnnotationNodeEntity.annotation_id == annotation_id)
                .where(
                    AnnotationNodeEntity.time.between(
                        time - threshold, time + threshold
                    )
                )
            )

            node = session.scalar(stmt)

        return node

    def add_node(self, node: AnnotationNodeEntity) -> AnnotationNodeEntity:
        with self.database.open_session() as session:
            session.add(node)
            session.commit()
            session.refresh(node)
        return node

    def add_nodes(
        self, nodes: list[AnnotationNodeEntity]
    ) -> list[AnnotationNodeEntity]:
        with self.database.open_session() as session:
            session.add_all(nodes)
            session.commit()
            for node in nodes:
                session.refresh(node)
        return nodes

    def delete_node_if_no_labels(self, node: AnnotationNodeEntity):
        with self.database.open_session() as session:
            has_label = session.scalar(
                select(
                    exists().where(
                        or_(
                            AnnotationLabelEntity.start_node_id == node.id,
                            AnnotationLabelEntity.end_node_id == node.id,
                        )
                    )
                )
            )
            if not has_label:
                session.delete(node)
            session.commit()

    def add_types(self, types: list[AnnotationTypeEntity]):
        with self.database.open_session() as session:
            session.add_all(types)
            session.commit()

    def add_label(self, label: AnnotationLabelEntity):
        with self.database.open_session() as session:
            session.add(label)
            session.commit()

    def merge_label(self, label: AnnotationLabelEntity):
        with self.database.open_session() as session:
            old_s_node, old_e_node = None, None
            old_label = session.get(AnnotationLabelEntity, label.id)
            if old_label is not None:
                old_s_node = old_label.start_node
                old_e_node = old_label.end_node

            session.merge(label)
            for node in (old_s_node, old_e_node):
                if node is not None:
                    self.delete_node_if_no_labels(node)

            session.commit()

    def delete_label(self, label: AnnotationLabelEntity):
        with self.database.open_session() as session:
            label = session.merge(label)
            session.delete(label)
            for node in (label.start_node, label.end_node):
                if node is not None:
                    self.delete_node_if_no_labels(node)
            session.commit()
