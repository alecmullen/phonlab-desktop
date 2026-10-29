from sqlalchemy.orm import Mapped, mapped_column

from data.base.base_entity import BaseEntity


class AnnotationTypeEntity(BaseEntity):
    __table_name__ = "annotation_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    