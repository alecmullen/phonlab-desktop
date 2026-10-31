from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data.annotation.entity.annotation_label import AnnotationLabelEntity
from data.base.base_entity import BaseEntity


class AnnotationTypeEntity(BaseEntity):
    __tablename__ = "annotation_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    annotation_id: Mapped[int] = mapped_column(ForeignKey("annotation.id"))
    name: Mapped[str] = mapped_column(String(255))

    labels: Mapped[list[AnnotationLabelEntity]] = relationship(
        cascade="all, delete-orphan"
    )
