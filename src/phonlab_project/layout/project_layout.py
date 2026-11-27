from dataclasses import dataclass
from enum import Enum

from phonlab_project.constants import LAYOUT_VERSION, PROJECT_AUDIO_EXTENSIONS
from phonlab_project.readers.table_format import TableFormat


def is_within(directory: str, folder: str) -> bool:
    """Whether `directory` is `folder` or inside it; every directory is within ``"""
    return folder == "" or directory == folder or directory.startswith(folder + "/")


@dataclass(frozen=True)
class FolderLevel:
    """What the folders at one depth under the project folder represent.

    Attributes
    ----------

    depth : int
        1 for the folders in the project folder, 2 for those inside them...

    field : str
        The variable the folder names are values of (`talker`, `dialect`...). The
        variable `talker` makes them the talkers of the recordings. Empty if the level
        is only organizational."""

    depth: int
    field: str = ""


class DataFileKind(Enum):
    """What a kind of file that goes with each recording is for: `OTHER`, `TIME_SERIES` (a
    track such as formants) or `ANNOTATION` (a tier of the recording's annotation)."""

    OTHER = "other"
    TIME_SERIES = "time_series"
    ANNOTATION = "annotation"  # a tier of the recording's annotation


@dataclass(frozen=True)
class DataFileRole:
    """A kind of file that goes with each recording.

    The file is named like the sound file plus `suffix`, with extension `ext`.

    Attributes
    ----------

    name : str
        What the kind of file is called.

    suffix : str
        What follows the sound file's name (`_phn`).

    ext : str
        The extension, in lower case with the dot.

    kind : DataFileKind
        What the files are for.

    tier : str
        For an annotation, the name of the tier it holds (the `name` by default).

    table : TableFormat or None
        For an annotation, how to read the file as a table (None: work it out)."""

    name: str
    suffix: str = ""
    ext: str = ""
    kind: DataFileKind = DataFileKind.OTHER
    tier: str = ""
    # how to read the files of an annotation kind as a table (None: work it out)
    table: TableFormat | None = None

    @property
    def tier_name(self) -> str:
        return self.tier or self.name

    @property
    def key(self) -> tuple[str, str]:
        return (self.suffix.casefold(), self.ext)


@dataclass(frozen=True)
class ChannelRole:
    """One channel of a recording stored as a sound file for each channel.

    Attributes
    ----------

    label : str
        The name of the channel (`L`).

    suffix : str
        What the file name has after the recording's name (`_L`).

    talker : str
        Who is on the channel, if known."""

    label: str
    suffix: str
    talker: str = ""

    @property
    def key(self) -> str:
        return self.suffix.casefold()


@dataclass(frozen=True)
class ProjectLayout:
    """How a project folder is organized.

    It is saved in the project's `phonlab.toml` (see `save_layout`) so that the project
    is read the same way each time. The TOML can be edited by hand.

    Attributes
    ----------

    audio_ext : tuple of str
        Extensions of sound files.

    annotation_ext : str or None
        Extension of the annotation files (`.textgrid`, `.eaf`, `.srt`, `.cha`,
        `.words`, `.wrd`); None if there are none.

    annotation_dir : str
        Where annotation files are read from, as a folder relative to the project. Empty
        means anywhere, which is wrong when several folders hold annotations of the same
        recordings.

    include_unpaired_audio : bool
        Whether sound files with no annotation are recordings of the project.

    levels : tuple of FolderLevel
        What the folders at each depth are.

    filename_template : str
        Takes variables from sound file names, such as `{talker}_{item:d}`.

    data_files : tuple of DataFileRole
        Other files that go with each recording (formant tracks, tiers in text tables).

    channels : tuple of ChannelRole
        Empty unless recordings are stored as separate sound files, one per channel.

    version : int
        The version of the layout format."""

    audio_ext: tuple[str, ...] = PROJECT_AUDIO_EXTENSIONS
    annotation_ext: str | None = ".textgrid"
    # Where annotation files are read from, as a folder relative to the project
    # directory. Empty means anywhere, which is wrong when several folders hold
    # annotations of the same recordings.
    annotation_dir: str = ""
    include_unpaired_audio: bool = True
    levels: tuple[FolderLevel, ...] = ()
    filename_template: str = ""
    data_files: tuple[DataFileRole, ...] = ()
    # empty unless recordings are stored as separate audio files, one per channel
    channels: tuple[ChannelRole, ...] = ()
    version: int = LAYOUT_VERSION

    def reads_annotations_from(self, directory: str) -> bool:
        """Whether annotation files in `directory` (relative to the project) count"""
        return is_within(directory, self.annotation_dir)
