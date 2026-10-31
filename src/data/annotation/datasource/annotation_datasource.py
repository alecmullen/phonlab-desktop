from sqlalchemy import select
from sqlalchemy.orm import joinedload

from data.annotation.entity.annotation import AnnotationEntity
from data.annotation.entity.annotation_node import AnnotationNodeEntity
from data.annotation.entity.annotation_type import AnnotationTypeEntity
from data.base.datasource import DataSource


class AnnotationDataSource(DataSource):
    def find_annotation_by_filename(self, filename: str) -> AnnotationEntity | None:
        with self.database.open_session() as session:
            stmt = (
                select(AnnotationEntity)
                .where(AnnotationEntity.file_name == filename)
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

    def add_nodes(
        self, nodes: list[AnnotationNodeEntity]
    ) -> list[AnnotationNodeEntity]:
        with self.database.open_session() as session:
            session.add_all(nodes)
            session.commit()
            for node in nodes:
                session.refresh(node)
        return nodes

    def add_types(self, types: list[AnnotationTypeEntity]):
        with self.database.open_session() as session:
            session.add_all(types)
            session.commit()
