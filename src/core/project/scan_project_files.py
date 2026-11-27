from phonlab_project.layout.plan_project import (
    is_annotation_file,
    is_audio_file,
    matching_annotation_files,
    plan_project,
)
from phonlab_project.layout.project_file import ProjectFile

__all__ = [
    "is_annotation_file",
    "is_audio_file",
    "matching_annotation_files",
    "scan_project_files",
]


def scan_project_files(dir_path: str) -> list[ProjectFile]:
    """Every recording in dir_path, paired with its TextGrid if it has one, with its
    extra files and talkers attached. The layout saved in the project says where to
    look and how files belong together; a project without one is read the way it
    appears to be organized (a flat folder of sound files and TextGrids, for one)."""
    return plan_project(dir_path).files
