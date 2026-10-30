from sqlalchemy import select

from data.annotation.entity.annotation import AnnotationEntity
from data.annotation.entity.annotation_node import AnnotationNodeEntity
from data.base.datasource import DataSource


class AnnotationDataSource(DataSource):
    def get_annotation_by_filename(self, filename: str) -> AnnotationEntity | None:
        with self.database.open_session() as session:
            stmt = select(AnnotationEntity).where(
                AnnotationEntity.file_name == filename
            )
            annotation = session.scalar(stmt)

        return annotation

    def save_annotation(self, annotation: AnnotationEntity) -> AnnotationEntity:
        with self.database.open_session() as session:
            session.merge(annotation)
            session.flush()
            session.commit()
            session.refresh(annotation)
        return annotation

    def save_nodes(
        self, nodes: list[AnnotationNodeEntity]
    ) -> list[AnnotationNodeEntity]:
        with self.database.open_session() as session:
            session.add_all(nodes)
            session.flush()
            session.commit()
            for node in nodes:
                session.refresh(node)
        return nodes
