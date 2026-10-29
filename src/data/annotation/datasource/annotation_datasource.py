from sqlalchemy import select

from data.annotation.entity.annotation import AnnotationEntity
from data.base.datasource import DataSource


class AnnotationDataSource(DataSource):
    def get_annotation(self, id: int) -> AnnotationEntity | None:
        with self.database.open_session() as session:
            stmt = select(AnnotationEntity).where(AnnotationEntity.id == id)
            annotation = session.scalar(stmt)

        return annotation

    def save_annotation(self, annotation: AnnotationEntity):
        with self.database.open_session() as session:
            session.add(annotation)
            session.commit()
