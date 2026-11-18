from dataclasses import dataclass, field

from core.annotation.entity.recording import Recording
from core.read_tiers.entity.table_format import TierFile


@dataclass(frozen=True)
class ProjectFile:
    """An audio file in a project directory and its TextGrid, if there is one, and the
    files that hold further tiers of its annotation (tier name -> file).
    file_stem is the audio file's path relative to the project directory, minus the
    suffix. For a recording stored as one audio file per channel, audio_path is its
    first channel's file.

    `recording` is what the project's layout says about the file (its talkers, extra
    files, channels...); it is not part of what makes two project files equal."""

    file_stem: str
    audio_path: str
    textgrid_path: str | None = None
    recording: Recording | None = field(default=None, compare=False)
    tier_files: dict[str, TierFile] = field(default_factory=dict)
