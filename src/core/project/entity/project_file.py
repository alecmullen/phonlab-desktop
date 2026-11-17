from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectFile:
    """An audio file in a project directory and its TextGrid, if there is one.
    file_stem is the audio file's path relative to the project directory, minus the
    suffix"""

    file_stem: str
    audio_path: str
    textgrid_path: str | None = None
