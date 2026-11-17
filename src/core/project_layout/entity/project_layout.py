from dataclasses import dataclass

from res.constants import (
    LAYOUT_VERSION,
    PROJECT_AUDIO_EXTENSIONS,
)


def is_within(directory: str, folder: str) -> bool:
    """Whether `directory` is `folder` or inside it; every directory is within ``"""
    return folder == "" or directory == folder or directory.startswith(folder + "/")


@dataclass(frozen=True)
class FolderLevel:
    """What the folders at one depth under the project directory represent.
    An empty `field` means the level is only organizational."""

    depth: int
    field: str = ""


@dataclass(frozen=True)
class DataFileRole:
    """A kind of file that goes with each recording: the file named like the audio
    file plus `suffix`, with extension `ext` (casefolded, with the dot)"""

    name: str
    suffix: str = ""
    ext: str = ""

    @property
    def key(self) -> tuple[str, str]:
        return (self.suffix.casefold(), self.ext)


@dataclass(frozen=True)
class ChannelRole:
    """One channel of a recording stored as a file per channel: the audio file is
    named like the recording plus `suffix` (e.g. "_L"). `talker` is who is on the
    channel, if the user said."""

    label: str
    suffix: str
    talker: str = ""

    @property
    def key(self) -> str:
        return self.suffix.casefold()


@dataclass(frozen=True)
class ProjectLayout:
    """The description of how a project is organized. It is saved in the project's
    phonlab.toml so that the project can be imported again the same way."""

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
