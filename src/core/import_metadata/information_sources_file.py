import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from core.annotation.entity.metadata import MetadataTarget
from core.base.use_case_sync import UseCaseSync
from core.import_metadata.entity.information_source import InformationSource
from res.constants import INFORMATION_TOML_KEY

TOML_NAME = "phonlab.toml"


def stored_file_name(dir_path: str, csv_path: str) -> str:
    """How a CSV file is named in the project file: relative to the project directory
    when it is inside it, so the project can be moved, otherwise the full path"""
    path = Path(csv_path)
    try:
        return path.resolve().relative_to(Path(dir_path).resolve()).as_posix()
    except ValueError:
        return str(path)


def resolved_file_name(dir_path: str, stored: str) -> str:
    path = Path(stored)
    return str(path if path.is_absolute() else Path(dir_path) / path)


def _to_dict(source: InformationSource) -> dict[str, Any]:
    return {
        "file": source.file,
        "about": source.target.value,
        "key": source.key_column,
        "columns": dict(source.columns),
    }


def _from_dict(data: dict[str, Any]) -> InformationSource:
    """Raises ValueError for an entry that is not one this version understands"""
    try:
        return InformationSource(
            file=str(data["file"]),
            target=MetadataTarget(data["about"]),
            key_column=str(data["key"]),
            columns={str(k): str(v) for k, v in data.get("columns", {}).items()},
        )
    except (KeyError, TypeError, AttributeError) as err:
        raise ValueError(f"Invalid information entry: {err}") from err


class LoadInformationSources(UseCaseSync[list[InformationSource]]):
    """The CSV files whose information was added to the project, in the order they
    were added. Entries that cannot be understood are left out."""

    def __call__(self, dir_path: str) -> list[InformationSource]:
        try:
            with open(Path(dir_path) / TOML_NAME, "rb") as f:
                entries = tomllib.load(f).get(INFORMATION_TOML_KEY, [])
        except (OSError, tomllib.TOMLDecodeError):
            return []

        sources = []
        for entry in entries if isinstance(entries, list) else []:
            try:
                sources.append(_from_dict(entry))
            except ValueError:
                continue
        return sources


class SaveInformationSource(UseCaseSync[None]):
    """Remembers in the project file that a CSV file was added, replacing what it
    remembered about the same file (and kind of information), and keeping the rest of
    the project file"""

    def __call__(self, dir_path: str, source: InformationSource) -> None:
        path = Path(dir_path) / TOML_NAME
        data: dict[str, Any] = {}
        if path.exists():
            with open(path, "rb") as f:
                data = tomllib.load(f)

        kept = [
            entry
            for entry in data.get(INFORMATION_TOML_KEY, [])
            if not (
                entry.get("file") == source.file
                and entry.get("about") == source.target.value
            )
        ]
        data[INFORMATION_TOML_KEY] = [*kept, _to_dict(source)]
        with open(path, "wb") as f:
            tomli_w.dump(data, f)
