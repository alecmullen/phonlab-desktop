from pathlib import Path

from core.project_layout.entity.project_scan import ScannedFile


def find_duplicate_audio(audio: list[ScannedFile], root: str) -> list[str]:
    """Audio files that look like copies of another: the same name (ignoring case) in
    another folder and the same, non-zero size. Each is described as
    "copy.wav (same as original.wav)", the original being the first found."""
    by_name: dict[str, list[ScannedFile]] = {}
    for file in audio:
        by_name.setdefault(file.stem.casefold(), []).append(file)

    duplicates: list[str] = []
    for files in by_name.values():
        if len({file.dir for file in files}) < 2:
            continue
        original, *others = files
        size = _size(root, original)
        duplicates.extend(
            f"{other.path} (same as {original.path})"
            for other in others
            if other.dir != original.dir and size > 0 and _size(root, other) == size
        )
    return duplicates


def _size(root: str, file: ScannedFile) -> int:
    try:
        return (Path(root) / file.path).stat().st_size
    except OSError:
        return 0
