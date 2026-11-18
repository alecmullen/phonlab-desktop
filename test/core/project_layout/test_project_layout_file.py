from pathlib import Path

import pytest

from core.project_layout.entity.project_layout import (
    ChannelRole,
    DataFileKind,
    DataFileRole,
    FolderLevel,
    ProjectLayout,
)
from core.project_layout.project_layout_file import (
    LoadProjectLayout,
    SaveProjectLayout,
    layout_from_dict,
    layout_to_dict,
)
from core.read_tiers.entity.table_format import ColumnRole, TableFormat, TimeUnit

FULL_LAYOUT = ProjectLayout(
    annotation_ext=".words",
    annotation_dir="labels",
    include_unpaired_audio=False,
    levels=(FolderLevel(1, "dialect"), FolderLevel(2, "talker")),
    filename_template="{talker:3}{n:d}",
    data_files=(
        DataFileRole("pitch", "_f0", ".txt", DataFileKind.TIME_SERIES),
        DataFileRole(
            "phones",
            "_phn",
            ".txt",
            DataFileKind.ANNOTATION,
            "Phone",
            TableFormat(
                "\t",
                2,
                (ColumnRole.END, ColumnRole.START, ColumnRole.LABEL),
                TimeUnit.MILLISECONDS,
            ),
        ),
        DataFileRole("track", "", ".trk"),
    ),
    channels=(ChannelRole("L", "_L", "Ann"), ChannelRole("R", "_R")),
)


def test_layout_survives_a_round_trip_through_a_dict():
    assert layout_from_dict(layout_to_dict(FULL_LAYOUT)) == FULL_LAYOUT


def test_layout_without_annotations_survives_a_round_trip():
    layout = ProjectLayout(annotation_ext=None)

    assert layout_from_dict(layout_to_dict(layout)) == layout


def test_layout_from_a_newer_version_is_rejected():
    with pytest.raises(ValueError):
        layout_from_dict({"version": 99})


def test_layout_with_missing_keys_is_rejected():
    with pytest.raises(ValueError):
        layout_from_dict({"levels": [{"field": "talker"}]})


def test_load_returns_none_without_a_toml_or_section(tmp_path: Path):
    assert LoadProjectLayout()(str(tmp_path)) is None

    (tmp_path / "phonlab.toml").write_text("")

    assert LoadProjectLayout()(str(tmp_path)) is None


def test_load_returns_none_for_a_broken_toml(tmp_path: Path):
    (tmp_path / "phonlab.toml").write_text("this is [not toml")

    assert LoadProjectLayout()(str(tmp_path)) is None


def test_save_then_load_returns_the_same_layout(tmp_path: Path):
    SaveProjectLayout()(str(tmp_path), FULL_LAYOUT)

    assert LoadProjectLayout()(str(tmp_path)) == FULL_LAYOUT


def test_save_keeps_other_settings_in_the_toml(tmp_path: Path):
    (tmp_path / "phonlab.toml").write_text('[other]\nkey = "value"\n')

    SaveProjectLayout()(str(tmp_path), ProjectLayout())

    text = (tmp_path / "phonlab.toml").read_text()
    assert 'key = "value"' in text
    assert "[import]" in text


def test_save_replaces_an_earlier_layout(tmp_path: Path):
    SaveProjectLayout()(str(tmp_path), FULL_LAYOUT)
    SaveProjectLayout()(str(tmp_path), ProjectLayout())

    assert LoadProjectLayout()(str(tmp_path)) == ProjectLayout()
