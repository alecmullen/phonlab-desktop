from dataclasses import dataclass, field

from ui.base.state import State


@dataclass
class FolderLevelState(State):
    depth: int
    n_values: int
    examples: str
    field: str
    note: str


@dataclass
class DataFileRoleState(State):
    name: str
    pattern: str  # e.g. "*.xyz" or "*_f0.txt"
    n_files: int
    coverage_percent: int
    selected: bool
    kind: str  # "annotation", "time_series" or "other"
    tier: str  # the tier name, for an annotation


@dataclass
class ChannelRoleState(State):
    label: str
    suffix: str
    talker: str


@dataclass
class ChannelCandidateState(State):
    n_groups: int
    examples: str
    evidence: str


@dataclass
class FolderChoiceState(State):
    folder: str  # relative to the project; empty for the project folder itself
    n_files: int


@dataclass
class ProjectLayoutState(State):
    """Everything the import dialog shows. Paths are relative to the project."""

    n_audio: int = 0
    n_audio_files: int = 0
    n_recordings: int = 0
    n_annotated: int = 0
    n_unpaired_audio: int = 0
    n_unpaired_annotations: int = 0
    unpaired_audio_examples: list[str] = field(default_factory=list)
    unpaired_annotation_examples: list[str] = field(default_factory=list)
    n_duplicate_audio: int = 0
    duplicate_audio_examples: list[str] = field(default_factory=list)

    annotation_ext: str = ""
    annotation_exts: list[str] = field(default_factory=list)
    annotation_dir: str = ""
    annotation_folders: list[FolderChoiceState] = field(default_factory=list)
    # several folders hold annotations of the same recordings
    annotation_folders_overlap: bool = False
    include_unpaired_audio: bool = True

    channel_candidate: ChannelCandidateState | None = None
    channels_enabled: bool = False
    channels: list[ChannelRoleState] = field(default_factory=list)
    talker_names: list[str] = field(default_factory=list)

    levels: list[FolderLevelState] = field(default_factory=list)
    roles: list[DataFileRoleState] = field(default_factory=list)

    filename_template: str = ""
    template_error: str = ""
    n_template_mismatches: int = 0
    template_mismatch_examples: list[str] = field(default_factory=list)

    preview_headers: list[str] = field(default_factory=list)
    preview_rows: list[list[str]] = field(default_factory=list)

    can_import: bool = False
