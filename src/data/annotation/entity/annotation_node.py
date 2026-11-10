from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from data.base.base_entity import BaseEntity


class AnnotationNodeEntity(BaseEntity):
    __tablename__ = "annotation_node"

    id: Mapped[int] = mapped_column(primary_key=True)
    annotation_id: Mapped[int] = mapped_column(ForeignKey("annotation.id"))
    time: Mapped[float] = mapped_column()
