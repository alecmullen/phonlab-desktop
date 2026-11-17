from typing import NamedTuple


class OpenableFile(NamedTuple):
    """A recording to open: its stem relative to the project, its audio file, its
    annotation file if it has one, and, when the recording is stored as one audio
    file per channel, those files in channel order (absolute paths)"""

    file_stem: str
    audio_file: str
    annotation_file: str | None
    channel_files: tuple[str, ...] = ()
