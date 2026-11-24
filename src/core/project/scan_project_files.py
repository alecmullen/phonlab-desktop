import posixpath
from dataclasses import replace
from pathlib import Path

from core.annotation.entity.recording import Recording
from core.project.entity.project_file import ProjectFile
from core.project_layout.entity.project_scan import ProjectScan, ScannedFile
from core.project_layout.filename_template import TemplateError
from core.project_layout.infer_layout import InferLayout
from core.project_layout.project_layout_file import LoadProjectLayout
from core.project_layout.resolve_recordings import ResolveRecordings
from core.project_layout.scan_project_tree import ScanProjectTree
from core.read_tiers.entity.table_format import TierFile
from core.read_tiers.read_elan_info import read_elan_info
from res.constants import (
    AUDIO_FILE_SUFFIXES,
    PROJECT_VIDEO_EXTENSIONS,
    TEXTGRID_FILE_SUFFIXES,
)


def is_audio_file(path: str | Path) -> bool:
    return Path(path).suffix.lower() in AUDIO_FILE_SUFFIXES


def is_textgrid_file(path: str | Path) -> bool:
    return Path(path).suffix.lower() in TEXTGRID_FILE_SUFFIXES


def scan_project_files(dir_path: str) -> list[ProjectFile]:
    """Every recording in dir_path, paired with its TextGrid if it has one, with its
    extra files and talkers attached. The layout saved in the project says where to
    look and how files belong together; a project without one is read the way it
    appears to be organized (a flat folder of sound files and TextGrids, for one)."""
    scan = ScanProjectTree()(dir_path)
    layout = LoadProjectLayout()(dir_path)
    if layout is None:
        layout = InferLayout()(scan).layout

    try:
        recordings = ResolveRecordings()(scan, layout).recordings
    except TemplateError:
        # a template that cannot be used only loses the variables taken from names
        layout = replace(layout, filename_template="")
        recordings = ResolveRecordings()(scan, layout).recordings

    recordings = [_with_media_and_talkers(recording, scan) for recording in recordings]

    root = Path(dir_path)
    tables = {role.tier_name: role.table for role in layout.data_files}
    return [
        ProjectFile(
            recording.file_stem,
            str(root / recording.audio_file),
            str(root / recording.annotation_file)
            if recording.annotation_file
            else None,
            recording,
            {
                name: TierFile(str(root / path), tables.get(name))
                for name, path in recording.tier_files.items()
            },
        )
        for recording in recordings
        if recording.audio_file
    ]


def _with_media_and_talkers(recording: Recording, scan: ProjectScan) -> Recording:
    """The recording with its video, the offset of its media and its talkers, where
    the project has them: a video file named like the sound file, else the video an
    ELAN file names, and the offset the ELAN file gives the sound. The participants
    of an ELAN file are the talkers unless the layout has already given some."""
    if recording.audio_file is None:
        return recording
    videos = [f for f in scan.files if f.ext in PROJECT_VIDEO_EXTENSIONS]
    stem_path = posixpath.splitext(recording.audio_file)[0]
    video = next((f.path for f in videos if f.path_without_ext == stem_path), None)

    offset = None
    talkers = recording.talkers
    annotation = recording.annotation_file
    if annotation is not None and annotation.casefold().endswith(".eaf"):
        info = read_elan_info(
            str(Path(scan.root) / annotation), posixpath.basename(stem_path)
        )
        offset = info.offset
        talkers = talkers or list(info.participants)
        if video is None and info.video is not None:
            video = _find_video(info.video, annotation, videos)
    return replace(recording, video_file=video, media_offset=offset, talkers=talkers)


def _find_video(name: str, annotation: str, videos: list[ScannedFile]) -> str:
    """The path in the project of a video an ELAN file names: where the file says it
    is, relative to the file, else a video of that name anywhere in the project; if
    the project has none, the name as the file gives it"""
    relative = posixpath.normpath(posixpath.join(posixpath.dirname(annotation), name))
    paths = [f.path for f in videos]
    if relative in paths:
        return relative
    same_name = [p for p in paths if posixpath.basename(p) == posixpath.basename(name)]
    return min(same_name, key=len) if same_name else name
