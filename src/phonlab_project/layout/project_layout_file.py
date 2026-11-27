import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from phonlab_project.constants import LAYOUT_TOML_KEY, LAYOUT_VERSION
from phonlab_project.layout.project_layout import (
    ChannelRole,
    DataFileKind,
    DataFileRole,
    FolderLevel,
    ProjectLayout,
)
from phonlab_project.readers.table_format import ColumnRole, TableFormat, TimeUnit

TOML_NAME = "phonlab.toml"


def _table_to_dict(table: TableFormat) -> dict[str, Any]:
    return {
        "delimiter": table.delimiter,
        "skip": table.skip,
        "columns": [role.value for role in table.columns],
        "unit": table.unit.value,
    }


def _table_from_dict(data: dict[str, Any]) -> TableFormat:
    return TableFormat(
        str(data["delimiter"]),
        int(data["skip"]),
        tuple(ColumnRole(role) for role in data["columns"]),
        TimeUnit(data.get("unit", TimeUnit.AUTO.value)),
    )


def layout_to_dict(layout: ProjectLayout) -> dict[str, Any]:
    """The layout as the `[import]` table of `phonlab.toml`: `levels` (a list of
    `depth`, `field` and, if there is one, `template`), `filename` (`template`) and
    `talker` (`template`) are the parts that read folder and file names; see
    `ProjectLayout` for an example."""
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
            {
                "depth": level.depth,
                "field": level.field,
                **({"template": level.template} if level.template else {}),
            }
            for level in layout.levels
        ]
    if layout.filename_template:
        data["filename"] = {"template": layout.filename_template}
    if layout.talker_template:
        data["talker"] = {"template": layout.talker_template}
    if layout.data_files:
        data["data_files"] = [
            {
                "name": role.name,
                "suffix": role.suffix,
                "ext": role.ext,
                "kind": role.kind.value,
                "tier": role.tier,
                **({"table": _table_to_dict(role.table)} if role.table else {}),
            }
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
                FolderLevel(
                    int(level["depth"]),
                    str(level.get("field", "")),
                    str(level.get("template", "")),
                )
                for level in data.get("levels", ())
            ),
            filename_template=str(data.get("filename", {}).get("template", "")),
            talker_template=str(data.get("talker", {}).get("template", "")),
            data_files=tuple(
                DataFileRole(
                    str(role["name"]),
                    str(role.get("suffix", "")),
                    str(role.get("ext", "")).casefold(),
                    DataFileKind(role.get("kind", DataFileKind.OTHER.value)),
                    str(role.get("tier", "")),
                    _table_from_dict(role["table"]) if "table" in role else None,
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


def load_layout(dir_path: str) -> ProjectLayout | None:
    """Read the layout saved in a project's `phonlab.toml`.

    Parameters
    ----------

    dir_path : str
        The project folder.

    Returns
    -------

    layout : ProjectLayout or None
        None if there is no `phonlab.toml`, it has no layout, or it cannot be understood."""
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


def save_layout(dir_path: str, layout: ProjectLayout) -> None:
    """Save a layout in a project's `phonlab.toml`, keeping its other settings.

    The file is TOML and can be edited by hand. The layout is its `[import]` section (see
    `ProjectLayout` for its keys); other sections, such as `[corpus]` (see `save_corpus`),
    are left as they are.

    Parameters
    ----------

    dir_path : str
        The project folder.

    layout : ProjectLayout"""
    path = Path(dir_path) / TOML_NAME
    data: dict[str, Any] = {}
    if path.exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)
    data[LAYOUT_TOML_KEY] = layout_to_dict(layout)
    with open(path, "wb") as f:
        tomli_w.dump(data, f)
