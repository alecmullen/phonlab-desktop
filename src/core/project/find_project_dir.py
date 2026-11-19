from pathlib import Path

from res.constants import PROJECT_FILE_NAME


def find_project_dir(file_path: str | Path) -> str | None:
    path = Path(file_path).resolve()

    for directory in [*path.parents]:
        target = directory / PROJECT_FILE_NAME
        if target.is_file():
            return str(directory)

    return None
