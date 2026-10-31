from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data.annotation.entity.annotation_node import AnnotationNodeEntity
from data.annotation.entity.annotation_type import AnnotationTypeEntity
from data.base.base_entity import BaseEntity


class AnnotationEntity(BaseEntity):
    __tablename__ = "annotation"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255), unique=True)

    nodes: Mapped[list[AnnotationNodeEntity]] = relationship(
        cascade="all, delete-orphan",
    )
    types: Mapped[list[AnnotationTypeEntity]] = relationship(
        cascade="all, delete-orphan", order_by=AnnotationTypeEntity.id
    )

    def __repr__(self) -> str:
        return f"AnnotationEntity(id={self.id}, file_name={self.file_name})"
