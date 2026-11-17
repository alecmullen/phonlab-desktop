from dataclasses import dataclass, field


@dataclass(frozen=True)
class Recording:
    """What the project database keeps about one recording, next to its
    annotation: the files that belong to it and who is in it. Paths are relative
    to the project directory and use forward slashes."""

    file_stem: str
    # for a recording stored as one file per channel, the first channel's file
    audio_file: str | None = None
    annotation_file: str | None = None
    # channel label -> path, for recordings stored as one file per channel
    channel_files: dict[str, str] = field(default_factory=dict)
    # channel label -> talker on that channel
    channel_talkers: dict[str, str] = field(default_factory=dict)
    # kind of data file (e.g. a time series that goes with the audio) -> path
    data_files: dict[str, str] = field(default_factory=dict)
    talkers: list[str] = field(default_factory=list)
    # any other variable taken from the folder or file names (dialect, session...)
    fields: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RecordingUpsertResult:
    created: int = 0
    updated: int = 0
    removed: int = 0
