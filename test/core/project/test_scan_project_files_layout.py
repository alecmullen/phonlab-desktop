from pathlib import Path

from support.audio_files import write_wavs
from support.project_tree import make_tree, talker_tree

from core.annotation.entity.recording import Recording
from core.project.scan_project_files import scan_project_files
from core.project_layout.entity.project_layout import (
    ChannelRole,
    DataFileKind,
    DataFileRole,
    FolderLevel,
    ProjectLayout,
)
from core.project_layout.project_layout_file import SaveProjectLayout
from core.read_tiers.entity.table_format import ColumnRole, TableFormat, TierFile


def recordings_of(root: Path) -> list[Recording]:
    return [f.recording for f in scan_project_files(str(root)) if f.recording]


def test_a_project_without_a_saved_layout_is_read_as_it_appears(tmp_path: Path):
    talker_tree(tmp_path, annotated=2)

    recordings = recordings_of(tmp_path)

    assert len(recordings) == 8
    first = recordings[0]
    assert first.file_stem == "aa1/aa1_01"
    assert first.talkers == ["aa1"]  # the folder level that looks like the talker
    assert sorted(first.data_files) == ["pos", "trk"]


def test_the_saved_layout_says_how_to_read_the_project(tmp_path: Path):
    talker_tree(tmp_path, annotated=2)
    SaveProjectLayout()(
        str(tmp_path),
        ProjectLayout(levels=(FolderLevel(1, "group"),), include_unpaired_audio=False),
    )

    recordings = recordings_of(tmp_path)

    assert len(recordings) == 4  # only the annotated ones
    assert recordings[0].talkers == []
    assert recordings[0].fields == {"group": "aa1"}


def test_a_saved_template_that_cannot_be_used_only_loses_the_names(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "a.TextGrid"])
    SaveProjectLayout()(str(tmp_path), ProjectLayout(filename_template="{oops"))

    [recording] = recordings_of(tmp_path)

    assert recording.annotation_file == "a.TextGrid"


def test_channel_files_are_one_project_file_with_the_recording_attached(
    tmp_path: Path,
):
    write_wavs(tmp_path, ["a_L.wav", "a_R.wav"])
    make_tree(tmp_path, ["a.TextGrid"])
    SaveProjectLayout()(
        str(tmp_path),
        ProjectLayout(channels=(ChannelRole("L", "_L", "Ann"), ChannelRole("R", "_R"))),
    )

    [file] = scan_project_files(str(tmp_path))

    assert file.file_stem == "a"
    assert file.audio_path == str(tmp_path / "a_L.wav")
    assert file.textgrid_path == str(tmp_path / "a.TextGrid")
    assert file.recording is not None
    assert file.recording.channel_files == {"L": "a_L.wav", "R": "a_R.wav"}
    assert file.recording.talkers == ["Ann"]


def test_nested_projects_are_scanned_recursively(tmp_path: Path):
    make_tree(tmp_path, ["s1/a.wav", "s1/a.TextGrid", "s2/deeper/b.wav"])

    files = scan_project_files(str(tmp_path))

    assert [f.file_stem for f in files] == ["s1/a", "s2/deeper/b"]
    assert files[0].textgrid_path == str(tmp_path / "s1" / "a.TextGrid")


def test_files_of_annotation_kind_are_the_tier_files_of_the_project_file(
    tmp_path: Path,
):
    make_tree(tmp_path, ["s1.wav", "s1_phn.txt", "s1_wrd.txt"])
    SaveProjectLayout()(
        str(tmp_path),
        ProjectLayout(
            data_files=(
                DataFileRole("phn", "_phn", ".txt", DataFileKind.ANNOTATION, "Phone"),
                DataFileRole("wrd", "_wrd", ".txt", DataFileKind.ANNOTATION),
            )
        ),
    )

    [file] = scan_project_files(str(tmp_path))

    assert file.tier_files == {
        "Phone": TierFile(str(tmp_path / "s1_phn.txt")),
        "wrd": TierFile(str(tmp_path / "s1_wrd.txt")),
    }
    assert file.textgrid_path is None


def test_the_table_format_of_a_tier_file_goes_with_it(tmp_path: Path):
    make_tree(tmp_path, ["s1.wav", "s1_phn.txt"])
    table = TableFormat("\t", 1, (ColumnRole.START, ColumnRole.END, ColumnRole.LABEL))
    SaveProjectLayout()(
        str(tmp_path),
        ProjectLayout(
            data_files=(
                DataFileRole(
                    "phn", "_phn", ".txt", DataFileKind.ANNOTATION, "Phone", table
                ),
            )
        ),
    )

    [file] = scan_project_files(str(tmp_path))

    assert file.tier_files["Phone"].table == table
