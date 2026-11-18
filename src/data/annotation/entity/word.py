from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from data.base.base_entity import ON_DEMAND, BaseEntity


class WordEntity(BaseEntity):
    """A word of the table the user added to the project: the table is made when words
    are first added, and what the user's table says about each word (frequency, part of
    speech...) is added to it as columns."""

    __tablename__ = "word"
    __table_args__ = {"info": {ON_DEMAND: True}}  # noqa: RUF012

    id: Mapped[int] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(Text(), unique=True)
