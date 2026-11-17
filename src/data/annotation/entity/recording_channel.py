from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data.annotation.entity.talker import TalkerEntity
from data.base.base_entity import ON_DEMAND, BaseEntity


class RecordingChannelEntity(BaseEntity):
    """One channel of a recording that is stored as a separate audio file per
    channel, and the talker on it, if known. Recordings stored as a single audio
    file have no rows here, and a project that has no such recordings has no
    table: it is created when the first one is added."""

    __tablename__ = "recording_channel"
    __table_args__ = {"info": {ON_DEMAND: True}}  # noqa: RUF012

    id: Mapped[int] = mapped_column(primary_key=True)
    recording_id: Mapped[int] = mapped_column(ForeignKey("recording.id"))
    channel: Mapped[str] = mapped_column(String(255))
    audio_file: Mapped[str] = mapped_column(String(1024))
    talker_id: Mapped[int | None] = mapped_column(
        ForeignKey("talker.id"), nullable=True
    )

    talker: Mapped[TalkerEntity | None] = relationship()
