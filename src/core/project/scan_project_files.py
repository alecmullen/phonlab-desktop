from pathlib import Path

from core.project.entity.project_file import ProjectFile
from res.constants import AUDIO_FILE_SUFFIXES, TEXTGRID_FILE_SUFFIXES


def is_audio_file(path: str | Path) -> bool:
    return Path(path).suffix.lower() in AUDIO_FILE_SUFFIXES


def is_textgrid_file(path: str | Path) -> bool:
    return Path(path).suffix.lower() in TEXTGRID_FILE_SUFFIXES


def scan_project_files(dir_path: str) -> list[ProjectFile]:
    """Every audio file in dir_path, paired with its TextGrid if it has one. Suffixes
    are matched case-insensitively"""
    directory = Path(dir_path)

    def stem_of(path: Path) -> str:
        return path.relative_to(directory).with_suffix("").as_posix()

    paths = sorted(directory.glob("*"))
    textgrids = {stem_of(path): str(path) for path in paths if is_textgrid_file(path)}
    return [
        ProjectFile(stem_of(path), str(path), textgrids.get(stem_of(path)))
        for path in paths
        if is_audio_file(path)
    ]
