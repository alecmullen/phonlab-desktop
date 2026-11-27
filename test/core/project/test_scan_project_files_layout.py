from pathlib import Path

from support.audio_files import write_wavs
from support.project_tree import make_tree, talker_tree

from core.project.scan_project_files import scan_project_files
from core.project_layout.project_layout_file import SaveProjectLayout
from phonlab_project.layout.project_layout import (
    ChannelRole,
    DataFileKind,
    DataFileRole,
    FolderLevel,
    ProjectLayout,
)
from phonlab_project.readers.table_format import ColumnRole, TableFormat, TierFile
from phonlab_project.recording import Recording


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


# --------------------------- video and media offset ---------------------------

ELAN_WITH_MEDIA = """<?xml version="1.0" encoding="UTF-8"?>
<ANNOTATION_DOCUMENT FORMAT="3.0" VERSION="3.0">
<HEADER MEDIA_FILE="" TIME_UNITS="milliseconds">
<MEDIA_DESCRIPTOR MEDIA_URL="file:///x/a.wav" MIME_TYPE="audio/x-wav"
    RELATIVE_MEDIA_URL="./a.wav" TIME_ORIGIN="750"/>
{video}
</HEADER>
<TIME_ORDER/>
</ANNOTATION_DOCUMENT>
"""

VIDEO_DESCRIPTOR = (
    '<MEDIA_DESCRIPTOR MEDIA_URL="file:///x/a.mp4" MIME_TYPE="video/mp4" '
    'RELATIVE_MEDIA_URL="./a.mp4"/>'
)


def test_a_video_with_the_name_of_the_sound_file_is_kept_with_the_recording(
    tmp_path: Path,
):
    write_wavs(tmp_path, ["t1/a.wav"])
    make_tree(tmp_path, ["t1/a.mp4", "t1/b.mp4"])

    [recording] = recordings_of(tmp_path)

    assert recording.video_file == "t1/a.mp4"
    assert recording.media_offset is None


def test_an_elan_file_gives_the_offset_of_the_media_and_names_its_video(
    tmp_path: Path,
):
    write_wavs(tmp_path, ["a.wav"])
    (tmp_path / "a.eaf").write_text(ELAN_WITH_MEDIA.format(video=VIDEO_DESCRIPTOR))
    make_tree(tmp_path, ["videos/a.mp4"])

    [recording] = recordings_of(tmp_path)

    assert recording.media_offset == 0.75
    assert recording.video_file == "videos/a.mp4"  # found by its name


def test_a_video_the_project_does_not_have_is_kept_by_the_name_elan_gives(
    tmp_path: Path,
):
    write_wavs(tmp_path, ["a.wav"])
    (tmp_path / "a.eaf").write_text(ELAN_WITH_MEDIA.format(video=VIDEO_DESCRIPTOR))

    [recording] = recordings_of(tmp_path)

    assert recording.video_file == "a.mp4"


def test_the_participants_of_an_elan_file_are_the_talkers_of_its_recording(
    tmp_path: Path,
):
    write_wavs(tmp_path, ["a.wav"])
    (tmp_path / "a.eaf").write_text(
        ELAN_WITH_MEDIA.format(video="").replace(
            "<TIME_ORDER/>",
            '<TIME_ORDER/><TIER TIER_ID="x" PARTICIPANT="ann" LINGUISTIC_TYPE_REF="t"/>'
            '<TIER TIER_ID="y" PARTICIPANT="bob" LINGUISTIC_TYPE_REF="t"/>',
        )
    )

    [recording] = recordings_of(tmp_path)

    assert recording.talkers == ["ann", "bob"]


def test_talkers_the_layout_names_are_kept_as_the_target_talker_beside_participants(
    tmp_path: Path,
):
    write_wavs(tmp_path, ["aa1/a.wav"])
    (tmp_path / "aa1" / "a.eaf").write_text(
        ELAN_WITH_MEDIA.format(video="").replace(
            "<TIME_ORDER/>",
            '<TIME_ORDER/><TIER TIER_ID="x" PARTICIPANT="ann" LINGUISTIC_TYPE_REF="t"/>',
        )
    )
    SaveProjectLayout()(
        str(tmp_path),
        ProjectLayout(annotation_ext=".eaf", levels=(FolderLevel(1, "talker"),)),
    )

    [recording] = recordings_of(tmp_path)

    assert recording.talkers == ["ann"]  # as the file names them
    assert recording.target_talker == "aa1"  # as the layout does


def test_the_talkers_a_subtitle_file_names_are_the_talkers_of_its_recording(
    tmp_path: Path,
):
    write_wavs(tmp_path, ["a.wav"])
    (tmp_path / "a.srt").write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nAnn: Hi\n\n"
        "2\n00:00:01,000 --> 00:00:02,000\nBob: Hello\n\n"
        "3\n00:00:02,000 --> 00:00:03,000\nAnn: Bye\n"
    )

    [recording] = recordings_of(tmp_path)

    assert recording.talkers == ["Ann", "Bob"]
    assert recording.target_talker is None  # the layout named no talker


def test_a_subtitle_file_that_cannot_be_read_names_no_talkers(tmp_path: Path):
    write_wavs(tmp_path, ["a.wav"])
    (tmp_path / "a.srt").write_text("1\nnot a time\nAnn: Hi\n")

    [recording] = recordings_of(tmp_path)

    assert recording.talkers == []


def srt_text(talker: str) -> str:
    return f"1\n00:00:00,000 --> 00:00:01,000\n{talker}: Hi\n"


def test_subtitle_files_are_found_by_folder_and_filename_like_textgrids(
    tmp_path: Path,
):
    write_wavs(tmp_path, ["aa1/aa1_01.wav", "aa1/aa1_02.wav", "bb2/bb2_01.wav"])
    for stem in ("aa1/aa1_01", "aa1/aa1_02", "bb2/bb2_01"):
        (tmp_path / f"{stem}.srt").write_text(srt_text("Camille"))
    SaveProjectLayout()(
        str(tmp_path),
        ProjectLayout(
            annotation_ext=".srt",
            levels=(FolderLevel(1, "group"),),
            filename_template="{talker}_{item:d}",
        ),
    )

    recordings = {r.file_stem: r for r in recordings_of(tmp_path)}

    first = recordings["aa1/aa1_01"]
    assert first.annotation_file == "aa1/aa1_01.srt"
    assert first.fields["group"] == "aa1"
    assert first.talkers == ["Camille"]  # as the subtitles name them
    assert first.target_talker == "aa1"  # as the layout does
    assert first.fields["item"] == "01"
    assert recordings["bb2/bb2_01"].talkers == ["Camille"]
    assert recordings["bb2/bb2_01"].target_talker == "bb2"


def test_a_project_of_subtitle_files_is_read_as_it_appears(tmp_path: Path):
    write_wavs(tmp_path, ["aa1/aa1_01.wav", "bb2/bb2_01.wav"])
    (tmp_path / "aa1" / "aa1_01.srt").write_text(srt_text("Ann"))
    (tmp_path / "bb2" / "bb2_01.srt").write_text(srt_text("Bob"))

    recordings = {r.file_stem: r for r in recordings_of(tmp_path)}

    assert recordings["aa1/aa1_01"].annotation_file == "aa1/aa1_01.srt"
    assert recordings["aa1/aa1_01"].talkers == ["Ann"]
    assert recordings["aa1/aa1_01"].target_talker == "aa1"
