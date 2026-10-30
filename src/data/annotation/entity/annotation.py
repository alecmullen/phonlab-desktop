from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data.annotation.entity.annotation_node import AnnotationNodeEntity
from data.annotation.entity.annotation_type import AnnotationTypeEntity
from data.base.base_entity import BaseEntity


class AnnotationEntity(BaseEntity):
    __tablename__ = "annotation"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255))

    nodes: Mapped[list[AnnotationNodeEntity]] = relationship()
    types: Mapped[list[AnnotationTypeEntity]] = relationship()
