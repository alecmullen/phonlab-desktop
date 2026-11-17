from collections import Counter

from core.project_layout.entity.import_report import (
    FolderSources,
    SourceFolder,
)
from core.project_layout.entity.project_scan import ScannedFile
from core.project_layout.pairing import AudioIndex, reroot


def find_annotation_sources(
    annotations: list[ScannedFile], index: AudioIndex
) -> FolderSources:
    """Where annotation files are kept, as folders: the top-level ones, or when those
    still hold annotations of the same audio file, the subfolders that tell them apart
    (ann/v1 and ann/v2). Annotation files in the project folder itself are the folder "".

    Folders overlap when more than one of their annotation files belongs to the same
    audio file, as when each folder holds a version of the annotations; folders that
    hold different recordings (one per talker, say) are separate sources that do not
    overlap."""
    max_depth = max((_depth(file.dir) for file in annotations), default=1)

    best: tuple[int, int] | None = None
    chosen = (1, {})
    for depth in range(1, max(max_depth, 1) + 1):
        owners = _owners(annotations, index, depth)
        conflicting = any(
            count > 1
            for count in Counter(
                (_prefix(f.dir, depth), owners[f.path])
                for f in annotations
                if f.path in owners
            ).values()
        )
        if conflicting:
            continue
        key = (len(owners), -depth)  # the most files paired, then the shallowest
        if best is None or key > best:
            best, chosen = key, (depth, owners)
    if best is None:
        chosen = (max_depth, _owners(annotations, index, max_depth))
    depth, owners = chosen

    groups: dict[str, list[ScannedFile]] = {}
    for file in annotations:
        groups.setdefault(_prefix(file.dir, depth), []).append(file)
    folders = [
        SourceFolder(folder, len(files), sum(1 for f in files if f.path in owners))
        for folder, files in sorted(groups.items())
    ]
    overlapping = len(set(owners.values())) < len(owners)
    # the folder with the most annotations that belong to audio files
    most_paired = max(folders, key=lambda f: f.n_paired, default=None)
    return FolderSources(
        folders, overlapping, most_paired.folder if overlapping and most_paired else ""
    )


def _owners(
    annotations: list[ScannedFile], index: AudioIndex, depth: int
) -> dict[str, str]:
    """Annotation file -> the audio file it belongs to, with the annotations read
    from the folders `depth` levels down"""
    owners: dict[str, str] = {}
    for file in annotations:
        found = index.owner(file, allow_suffix=False)
        folder = _prefix(file.dir, depth)
        if found is None and folder:
            found = index.owner(reroot(file, folder), allow_suffix=False)
        if found is not None:
            owners[file.path] = found[0].path
    return owners


def _depth(directory: str) -> int:
    return len(directory.split("/")) if directory else 0


def _prefix(directory: str, depth: int) -> str:
    return "/".join(directory.split("/")[:depth]) if directory else ""
