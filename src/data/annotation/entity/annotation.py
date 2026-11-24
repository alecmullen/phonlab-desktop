from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data.annotation.entity.annotation_node import AnnotationNodeEntity
from data.annotation.entity.annotation_type import AnnotationTypeEntity
from data.annotation.entity.recording_talker import RecordingTalkerEntity
from data.base.base_entity import BaseEntity


class AnnotationEntity(BaseEntity):
    __tablename__ = "recording"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_stem: Mapped[str] = mapped_column(String(255), unique=True)

    # Project import: the files that belong to this recording. Paths are relative to
    # the project directory. Who is in the recording is in `talker_links`, and the
    # audio files of a recording stored as one file per channel are in the
    # recording_channel table, which a project has only if it has such recordings.
    # The columns `video_file` and `media_offset` (see RECORDING_MEDIA_COLUMNS) are
    # added when a recording first has a value for them.
    audio_file: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    annotation_file: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    data_files: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    fields: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)

    nodes: Mapped[list[AnnotationNodeEntity]] = relationship(
        cascade="all, delete-orphan",
    )
    types: Mapped[list[AnnotationTypeEntity]] = relationship(
        cascade="all, delete-orphan", order_by=AnnotationTypeEntity.id
    )
    talker_links: Mapped[list[RecordingTalkerEntity]] = relationship(
        cascade="all, delete-orphan", order_by=RecordingTalkerEntity.id
    )

    def __repr__(self) -> str:
        return f"AnnotationEntity(id={self.id}, file_stem={self.file_stem})"
