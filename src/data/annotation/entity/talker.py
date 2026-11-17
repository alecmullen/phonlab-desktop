from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from data.base.base_entity import BaseEntity


class TalkerEntity(BaseEntity):
    """A talker who is in at least one recording. Information about the talker (age,
    sex...) is added to this table as columns."""

    __tablename__ = "talker"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
