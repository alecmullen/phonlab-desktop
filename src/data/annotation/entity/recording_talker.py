from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data.annotation.entity.talker import TalkerEntity
from data.base.base_entity import BaseEntity


class RecordingTalkerEntity(BaseEntity):
    """Links a recording to a talker who is in it. A recording with several talkers
    has a row for each, in the order they were recorded"""

    __tablename__ = "recording_talker"
    __table_args__ = (UniqueConstraint("recording_id", "talker_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    recording_id: Mapped[int] = mapped_column(ForeignKey("recording.id"))
    talker_id: Mapped[int] = mapped_column(ForeignKey("talker.id"))

    talker: Mapped[TalkerEntity] = relationship()
