from dataclasses import replace
from pathlib import Path

from core.project.entity.project_file import ProjectFile
from core.project_layout.filename_template import TemplateError
from core.project_layout.infer_layout import InferLayout
from core.project_layout.project_layout_file import LoadProjectLayout
from core.project_layout.resolve_recordings import ResolveRecordings
from core.project_layout.scan_project_tree import ScanProjectTree
from core.read_tiers.entity.table_format import TierFile
from res.constants import AUDIO_FILE_SUFFIXES, TEXTGRID_FILE_SUFFIXES


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
