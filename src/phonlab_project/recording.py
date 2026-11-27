from dataclasses import dataclass, field


@dataclass(frozen=True)
class Recording:
    """What the project database keeps about one recording: its files and who is in it.

    Paths are relative to the project folder and use forward slashes.

    Attributes
    ----------

    file_stem : str
        The path of the recording without its extension (`aa1/aa1_01`); what names it in
        the database.

    audio_file : str or None
        The sound file. For a recording stored as one file per channel, the first.

    annotation_file : str or None
        The annotation file.

    tier_files : dict
        Tier name -> path, for tiers of the annotation kept in files of their own.

    channel_files : dict
        Channel -> path, for recordings stored as one sound file per channel.

    channel_talkers : dict
        Channel -> the talker on it.

    data_files : dict
        Kind of file -> path, for files that go with the recording (a formant track).

    video_file : str or None
        A video of the recording, if the project has one.

    media_offset : float or None
        How far, in seconds, the media is offset from the times of the annotation, as an
        ELAN file says. The times in the database are not changed.

    target_talker : str or None
        Who the folders and file names say is the talker, kept when the annotation file
        names talkers of its own, which are then `talkers`.

    tier_talkers : dict
        Tier name -> the talker who made the tier, for annotation files that name only
        roles, not people (CHAT: the tier `INV` is the talker `INV3` here). A tier that
        names its own talker keeps it.

    talkers : list of str
        Who is in the recording.

    fields : dict
        Other variables taken from folder and file names (`dialect`, `session`...)."""

    file_stem: str
    # for a recording stored as one file per channel, the first channel's file
    audio_file: str | None = None
    annotation_file: str | None = None
    # tier name -> path, for tiers of the annotation kept in files of their own
    tier_files: dict[str, str] = field(default_factory=dict)
    # channel label -> path, for recordings stored as one file per channel
    channel_files: dict[str, str] = field(default_factory=dict)
    # channel label -> talker on that channel
    channel_talkers: dict[str, str] = field(default_factory=dict)
    # kind of data file (e.g. a time series that goes with the audio) -> path
    data_files: dict[str, str] = field(default_factory=dict)
    # a video of the recording, if the project has one
    video_file: str | None = None
    # how far, in seconds, the media is offset from the times of the annotation, as
    # the annotation file (ELAN's) says; the times in the database are not changed
    media_offset: float | None = None
    # who the layout (folders and file names) says is the talker; kept when the
    # annotation file names talkers of its own, which are then `talkers`
    target_talker: str | None = None
    # tier name -> its talker, where the annotation file names roles, not people
    tier_talkers: dict[str, str] = field(default_factory=dict)
    talkers: list[str] = field(default_factory=list)
    # any other variable taken from the folder or file names (dialect, session...)
    fields: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RecordingUpsertResult:
    created: int = 0
    updated: int = 0
    removed: int = 0
