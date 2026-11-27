import os

from core.base.use_case_sync import UseCaseSync
from phonlab_project.layout.project_scan import ProjectScan, ScannedFile
from res.constants import PROJECT_IGNORED_NAMES


class ScanProjectTree(UseCaseSync[ProjectScan]):
    """Lists every file under a project directory without reading any of them.
    Hidden files and folders, and phonlab's own files, are left out."""

    def __call__(self, dir_path: str) -> ProjectScan:
        files: list[ScannedFile] = []

        def walk(abs_dir: str, rel_dir: str):
            try:
                entries = sorted(os.scandir(abs_dir), key=lambda entry: entry.name)
            except OSError:
                return
            for entry in entries:
                if entry.name.startswith("."):
                    continue
                rel_path = f"{rel_dir}/{entry.name}" if rel_dir else entry.name
                try:
                    if entry.is_dir():
                        walk(entry.path, rel_path)
                    elif entry.name not in PROJECT_IGNORED_NAMES:
                        files.append(ScannedFile.from_path(rel_path))
                except OSError:
                    continue

        walk(dir_path, "")
        return ProjectScan(dir_path, files)
