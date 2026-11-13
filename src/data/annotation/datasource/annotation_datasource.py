import time

from sqlalchemy import delete, exists, or_, select
from sqlalchemy.orm import selectinload

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
                    selectinload(AnnotationEntity.nodes),
                    selectinload(AnnotationEntity.types).selectinload(
                        AnnotationTypeEntity.labels
                    ),
                )
            )
            annotation = session.scalar(stmt)

        return annotation

    def get_annotation_by_id(self, id: int) -> AnnotationEntity:
        with self.database.open_session() as session:
            start_time = time.perf_counter()
            stmt = (
                select(AnnotationEntity)
                .where(AnnotationEntity.id == id)
                .options(
                    selectinload(AnnotationEntity.nodes),
                    selectinload(AnnotationEntity.types).selectinload(
                        AnnotationTypeEntity.labels
                    ),
                )
            )
            annotation = session.scalar(stmt)
            print("GET ANNOT:", time.perf_counter() - start_time)

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

    def clear_annotation(self, annotation_id: int):
        with self.database.open_session() as session:
            annotation = session.get(AnnotationEntity, annotation_id)
            if annotation is None:
                raise ValueError("Annotation with that id does not exist in database")
            annotation.types.clear()
            annotation.nodes.clear()
            session.commit()

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

    def update_node(self, node: AnnotationNodeEntity):
        with self.database.open_session() as session:
            session.merge(node)
            session.commit()

    def delete_node(self, node_id: int):
        with self.database.open_session() as session:
            stmt = delete(AnnotationNodeEntity).where(
                AnnotationNodeEntity.id == node_id
            )
            session.execute(stmt)
            session.commit()

    def delete_nodes_if_no_labels(self, node_ids: list[int]) -> list[int]:
        with self.database.open_session() as session:
            stmt = (
                delete(AnnotationNodeEntity)
                .where(
                    AnnotationNodeEntity.id.in_(node_ids),
                    ~exists().where(
                        or_(
                            AnnotationLabelEntity.start_node_id
                            == AnnotationNodeEntity.id,
                            AnnotationLabelEntity.end_node_id
                            == AnnotationNodeEntity.id,
                        )
                    ),
                )
                .returning(AnnotationNodeEntity.id)
            )
            result = session.execute(stmt)
            deleted_ids = [row.id for row in result.fetchall()]
            session.commit()

        return deleted_ids

    def add_types(self, types: list[AnnotationTypeEntity]):
        with self.database.open_session() as session:
            session.add_all(types)
            session.commit()

    def add_label(self, label: AnnotationLabelEntity) -> AnnotationLabelEntity:
        with self.database.open_session() as session:
            session.add(label)
            session.commit()
            session.refresh(label)
        return label

    def merge_label(self, label: AnnotationLabelEntity):
        with self.database.open_session() as session:
            session.merge(label)
            session.commit()

    def delete_label(self, label: AnnotationLabelEntity):
        with self.database.open_session() as session:
            label = session.merge(label)
            session.delete(label)
            session.commit()
