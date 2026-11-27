from dataclasses import dataclass, field

from phonlab_project.layout.project_layout import (
    ChannelRole,
    DataFileRole,
    ProjectLayout,
)
from phonlab_project.recording import Recording


@dataclass(frozen=True)
class ImportReport:
    """What applying a layout to a project found. Paths are relative to the
    project directory."""

    n_audio: int = 0  # recordings: a recording kept as one file per channel counts once
    n_audio_files: int = 0
    n_recordings: int = 0  # audio files that will be imported
    n_annotated: int = 0  # recordings that have an annotation file
    unpaired_audio: list[str] = field(default_factory=list)
    unpaired_annotations: list[str] = field(default_factory=list)
    # audio files that look like copies of others, as "copy.wav (same as a.wav)"
    duplicate_audio: list[str] = field(default_factory=list)
    # audio files whose names do not fit the filename template
    template_mismatches: list[str] = field(default_factory=list)
    # data file kind -> number of recordings that have one
    data_file_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ResolvedProject:
    recordings: list[Recording] = field(default_factory=list)
    report: ImportReport = field(default_factory=ImportReport)


@dataclass(frozen=True)
class LevelSummary:
    depth: int
    n_values: int
    examples: list[str]
    n_files: int
    # share of file names that start with the folder name
    name_prefix_share: float


@dataclass(frozen=True)
class DataFileCandidate:
    role: DataFileRole
    n_files: int
    coverage: float


@dataclass(frozen=True)
class ChannelCandidate:
    """Audio files that look like channels of one recording (a_L.wav, a_R.wav)"""

    roles: tuple[ChannelRole, ...]
    n_groups: int
    examples: list[str]
    # True if the files in the groups checked are mono and equally long, as channels
    # are; None if they could not be read
    looks_like_channels: bool | None = None


@dataclass(frozen=True)
class SourceFolder:
    """A folder (relative to the project) that holds annotation files"""

    folder: str
    n_files: int
    n_paired: int  # files that belong to an audio file


@dataclass(frozen=True)
class FolderSources:
    """The folders files of one kind (audio, or annotations of one format) are kept
    in. When several of them hold the same recordings (`overlapping`), the project
    has to say which one to read; `default` is the folder to read until it does,
    empty meaning any."""

    folders: list[SourceFolder] = field(default_factory=list)
    overlapping: bool = False
    default: str = ""

    @property
    def n_paired(self) -> int:
        """How many annotation files belong to audio files when the default folder is
        read"""
        read = [
            f for f in self.folders if f.folder == self.default or not self.overlapping
        ]
        return sum(f.n_paired for f in read)


@dataclass(frozen=True)
class LayoutSuggestion:
    layout: ProjectLayout
    levels: list[LevelSummary] = field(default_factory=list)
    data_file_candidates: list[DataFileCandidate] = field(default_factory=list)
    # annotation extension -> where its files are kept
    annotation_sources: dict[str, FolderSources] = field(default_factory=dict)
    channel_candidate: ChannelCandidate | None = None
