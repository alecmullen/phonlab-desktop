import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from core.base.use_case_sync import UseCaseSync
from core.project_layout.entity.project_layout import (
    ChannelRole,
    DataFileRole,
    FolderLevel,
    ProjectLayout,
)
from res.constants import LAYOUT_TOML_KEY, LAYOUT_VERSION

TOML_NAME = "phonlab.toml"


def layout_to_dict(layout: ProjectLayout) -> dict[str, Any]:
    data: dict[str, Any] = {
        "version": layout.version,
        "audio_ext": list(layout.audio_ext),
        "include_unpaired_audio": layout.include_unpaired_audio,
    }
    if layout.annotation_ext is not None:
        data["annotation_ext"] = layout.annotation_ext
    if layout.annotation_dir:
        data["annotation_dir"] = layout.annotation_dir
    if layout.levels:
        data["levels"] = [
            {"depth": level.depth, "field": level.field} for level in layout.levels
        ]
    if layout.filename_template:
        data["filename"] = {"template": layout.filename_template}
    if layout.data_files:
        data["data_files"] = [
            {"name": role.name, "suffix": role.suffix, "ext": role.ext}
            for role in layout.data_files
        ]
    if layout.channels:
        data["channels"] = [
            {"label": role.label, "suffix": role.suffix, "talker": role.talker}
            for role in layout.channels
        ]
    return data


def layout_from_dict(data: dict[str, Any]) -> ProjectLayout:
    """Raises ValueError if the data is not a layout this version understands"""
    try:
        version = int(data.get("version", LAYOUT_VERSION))
        if version > LAYOUT_VERSION:
            raise ValueError(f"Project layout version {version} is too new")
        defaults = ProjectLayout()
        return ProjectLayout(
            audio_ext=tuple(str(e).casefold() for e in data.get("audio_ext", ()))
            or defaults.audio_ext,
            annotation_ext=(
                str(data["annotation_ext"]).casefold()
                if "annotation_ext" in data
                else None
            ),
            annotation_dir=str(data.get("annotation_dir", "")),
            include_unpaired_audio=bool(data.get("include_unpaired_audio", True)),
            levels=tuple(
                FolderLevel(int(level["depth"]), str(level.get("field", "")))
                for level in data.get("levels", ())
            ),
            filename_template=str(data.get("filename", {}).get("template", "")),
            data_files=tuple(
                DataFileRole(
                    str(role["name"]),
                    str(role.get("suffix", "")),
                    str(role.get("ext", "")).casefold(),
                )
                for role in data.get("data_files", ())
            ),
            channels=tuple(
                ChannelRole(
                    str(role["label"]),
                    str(role["suffix"]),
                    str(role.get("talker", "")),
                )
                for role in data.get("channels", ())
            ),
            version=version,
        )
    except (KeyError, TypeError, AttributeError) as err:
        raise ValueError(f"Invalid project layout: {err}") from err


class LoadProjectLayout(UseCaseSync[ProjectLayout | None]):
    """The layout saved in the project's phonlab.toml, or None if there is none
    (or it cannot be understood)"""

    def __call__(self, dir_path: str) -> ProjectLayout | None:
        path = Path(dir_path) / TOML_NAME
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
            section = data.get(LAYOUT_TOML_KEY)
            if not isinstance(section, dict):
                return None
            return layout_from_dict(section)
        except (OSError, tomllib.TOMLDecodeError, ValueError):
            return None


class SaveProjectLayout(UseCaseSync[None]):
    """Saves the layout in the project's phonlab.toml, keeping its other settings"""

    def __call__(self, dir_path: str, layout: ProjectLayout) -> None:
        path = Path(dir_path) / TOML_NAME
        data: dict[str, Any] = {}
        if path.exists():
            with open(path, "rb") as f:
                data = tomllib.load(f)
        data[LAYOUT_TOML_KEY] = layout_to_dict(layout)
        with open(path, "wb") as f:
            tomli_w.dump(data, f)
