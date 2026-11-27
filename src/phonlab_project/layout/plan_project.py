import posixpath
from dataclasses import replace
from pathlib import Path

from phonlab_project.constants import (
    AUDIO_FILE_SUFFIXES,
    PROJECT_VIDEO_EXTENSIONS,
    SINGLE_FILE_ANNOTATION_SUFFIXES,
)
from phonlab_project.layout.chat_speakers import name_chat_speakers
from phonlab_project.layout.filename_template import TemplateError
from phonlab_project.layout.infer_layout import infer_layout
from phonlab_project.layout.project_file import ProjectFile
from phonlab_project.layout.project_layout import ProjectLayout
from phonlab_project.layout.project_layout_file import load_layout
from phonlab_project.layout.project_plan import LayoutSource, ProjectPlan
from phonlab_project.layout.project_scan import ProjectScan, ScannedFile
from phonlab_project.layout.resolve_recordings import resolve_recordings
from phonlab_project.layout.scan_project_tree import scan_project_tree
from phonlab_project.readers.read_elan_info import read_elan_info
from phonlab_project.readers.read_srt import read_srt_tiers
from phonlab_project.readers.table_format import TierFile
from phonlab_project.recording import Recording


def is_audio_file(path: str | Path) -> bool:
    return Path(path).suffix.lower() in AUDIO_FILE_SUFFIXES


def is_annotation_file(path: str | Path) -> bool:
    """Whether the file is one that can be opened with a sound file: a TextGrid, an
    ELAN file or a subtitle file"""
    return Path(path).suffix.lower() in SINGLE_FILE_ANNOTATION_SUFFIXES


def matching_annotation_files(audio_file: str | Path) -> list[str]:
    """The annotation files in the folder of a sound file that are named like it
    (`a.TextGrid`, `a.eaf` and `a.srt` for `a.wav`), TextGrids first"""
    audio = Path(audio_file)
    if not audio.parent.is_dir():
        return []
    names = {path.name.casefold(): path for path in audio.parent.iterdir()}
    return [
        str(names[key])
        for suffix in SINGLE_FILE_ANNOTATION_SUFFIXES
        if (key := f"{audio.stem}{suffix}".casefold()) in names
    ]


def plan_project(dir_path: str, layout: ProjectLayout | None = None) -> ProjectPlan:
    """What reading the project in dir_path finds, with nothing written: its recordings
    (see `scan_project_files`) and what did not fit. The layout is the one given, else
    the one saved in the project, else one inferred from the files."""
    scan = scan_project_tree(dir_path)
    suggestion = None
    if layout is not None:
        source: LayoutSource = "given"
    elif (layout := load_layout(dir_path)) is not None:
        source = "saved"
    else:
        suggestion = infer_layout(scan)
        layout, source = suggestion.layout, "inferred"

    template_unusable = False
    try:
        resolved = resolve_recordings(scan, layout)
    except TemplateError:
        # a template that cannot be used only loses the variables taken from names
        layout = replace(layout, filename_template="")
        resolved = resolve_recordings(scan, layout)
        template_unusable = True

    recordings = name_chat_speakers(
        [_with_media_and_talkers(recording, scan) for recording in resolved.recordings],
        dir_path,
    )

    root = Path(dir_path)
    tables = {role.tier_name: role.table for role in layout.data_files}
    files = [
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
    return ProjectPlan(
        dir_path, layout, source, files, resolved.report, suggestion, template_unusable
    )


def _with_media_and_talkers(recording: Recording, scan: ProjectScan) -> Recording:
    """The recording with its video, the offset of its media and its talkers, where
    the project has them: a video file named like the sound file, else the video an
    ELAN file names, and the offset the ELAN file gives the sound. When an ELAN or
    subtitle file names talkers they are the talkers of the recording; the talkers the
    layout gave it are kept as its target talker."""
    if recording.audio_file is None:
        return recording
    videos = [f for f in scan.files if f.ext in PROJECT_VIDEO_EXTENSIONS]
    stem_path = posixpath.splitext(recording.audio_file)[0]
    video = next((f.path for f in videos if f.path_without_ext == stem_path), None)

    offset = None
    in_file: list[str] = []
    annotation = recording.annotation_file
    if annotation is not None and annotation.casefold().endswith(".eaf"):
        info = read_elan_info(
            str(Path(scan.root) / annotation), posixpath.basename(stem_path)
        )
        offset = info.offset
        in_file = list(info.participants)
        if video is None and info.video is not None:
            video = _find_video(info.video, annotation, videos)
    elif annotation is not None and annotation.casefold().endswith(".srt"):
        in_file = _srt_talkers(str(Path(scan.root) / annotation))

    talkers, target = recording.talkers, None
    if in_file:
        target = ", ".join(talkers) or None
        talkers = in_file
    return replace(
        recording,
        video_file=video,
        media_offset=offset,
        target_talker=target,
        talkers=talkers,
    )


def _srt_talkers(path: str) -> list[str]:
    """The talkers a subtitle file names; a file that cannot be read names none"""
    try:
        tiers = read_srt_tiers(path)
    except (ValueError, OSError):
        return []
    return [tier["talker"] for tier in tiers if "talker" in tier]


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
