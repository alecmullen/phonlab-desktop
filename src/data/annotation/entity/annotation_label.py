from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data.annotation.entity.annotation_node import AnnotationNodeEntity
from data.base.base_entity import BaseEntity


class AnnotationLabelEntity(BaseEntity):
    __tablename__ = "annotation_label"

    id: Mapped[int] = mapped_column(primary_key=True)
    annotation_type_id: Mapped[int] = mapped_column(ForeignKey("annotation_type.id"))
    label_text: Mapped[str] = mapped_column(Text())
    start_node_id: Mapped[int] = mapped_column(ForeignKey("annotation_node.id"))
    end_node_id: Mapped[int] = mapped_column(ForeignKey("annotation_node.id"))

    start_node: Mapped[AnnotationNodeEntity] = relationship(
        foreign_keys=[start_node_id]
    )
    end_node: Mapped[AnnotationNodeEntity] = relationship(foreign_keys=[end_node_id])
