from pathlib import Path

from support.project_tree import make_tree, talker_tree, write_audio_like

from core.project_layout.entity.import_report import ResolvedProject
from core.project_layout.entity.project_layout import (
    DataFileRole,
    FolderLevel,
    ProjectLayout,
)
from core.project_layout.resolve_recordings import ResolveRecordings
from core.project_layout.scan_project_tree import ScanProjectTree


def resolve(root: Path, layout: ProjectLayout) -> ResolvedProject:
    return ResolveRecordings()(ScanProjectTree()(str(root)), layout)


def test_flat_project_pairs_audio_with_annotation(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "a.TextGrid", "b.wav"])

    result = resolve(tmp_path, ProjectLayout())

    assert [(r.file_stem, r.annotation_file) for r in result.recordings] == [
        ("a", "a.TextGrid"),
        ("b", None),
    ]
    assert result.report.unpaired_audio == ["b.wav"]
    assert result.report.n_annotated == 1


def test_unpaired_audio_can_be_left_out_but_is_still_reported(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "a.TextGrid", "b.wav"])

    result = resolve(tmp_path, ProjectLayout(include_unpaired_audio=False))

    assert [r.file_stem for r in result.recordings] == ["a"]
    assert result.report.unpaired_audio == ["b.wav"]
    assert result.report.n_audio == 2
    assert result.report.n_recordings == 1


def test_annotation_without_audio_is_reported(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "a.TextGrid", "orphan.TextGrid"])

    result = resolve(tmp_path, ProjectLayout())

    assert result.report.unpaired_annotations == ["orphan.TextGrid"]


def test_pairing_ignores_case_of_name_and_extension(tmp_path: Path):
    make_tree(tmp_path, ["Take1.WAV", "take1.textgrid"])

    [recording] = resolve(tmp_path, ProjectLayout()).recordings

    assert recording.annotation_file == "take1.textgrid"


def test_parallel_trees_are_paired_by_matching_folders(tmp_path: Path):
    make_tree(
        tmp_path,
        ["audio/t1/a.wav", "audio/t2/a.wav", "labels/t1/a.TextGrid"],
    )

    result = resolve(tmp_path, ProjectLayout())

    assert {r.file_stem: r.annotation_file for r in result.recordings} == {
        "audio/t1/a": "labels/t1/a.TextGrid",
        "audio/t2/a": None,
    }


def test_ambiguous_partner_in_another_folder_is_not_guessed(tmp_path: Path):
    make_tree(tmp_path, ["one/a.wav", "two/a.wav", "labels/a.TextGrid"])

    result = resolve(tmp_path, ProjectLayout())

    assert all(r.annotation_file is None for r in result.recordings)
    assert result.report.unpaired_annotations == ["labels/a.TextGrid"]


def test_data_files_are_attached_by_kind(tmp_path: Path):
    make_tree(
        tmp_path,
        ["a.wav", "a.trk", "a_f0.txt", "b.wav", "b.trk", "unrelated.trk"],
    )
    layout = ProjectLayout(
        data_files=(
            DataFileRole("track", "", ".trk"),
            DataFileRole("pitch", "_f0", ".txt"),
        )
    )

    result = resolve(tmp_path, layout)

    assert {r.file_stem: r.data_files for r in result.recordings} == {
        "a": {"track": "a.trk", "pitch": "a_f0.txt"},
        "b": {"track": "b.trk"},
    }
    assert result.report.data_file_counts == {"track": 2, "pitch": 1}


def test_data_file_kinds_that_are_not_selected_are_left_out(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "a.trk", "a.pos"])

    [recording] = resolve(
        tmp_path, ProjectLayout(data_files=(DataFileRole("track", "", ".trk"),))
    ).recordings

    assert recording.data_files == {"track": "a.trk"}


def test_longest_matching_audio_name_owns_a_data_file(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "a_2.wav", "a_2.trk"])

    result = resolve(
        tmp_path, ProjectLayout(data_files=(DataFileRole("track", "", ".trk"),))
    )

    assert {r.file_stem: r.data_files for r in result.recordings} == {
        "a": {},
        "a_2": {"track": "a_2.trk"},
    }


def test_folder_levels_and_filename_fields_become_talkers_and_fields(tmp_path: Path):
    make_tree(tmp_path, ["north/aa1/aa1_03.wav"])
    layout = ProjectLayout(
        levels=(FolderLevel(1, "dialect"), FolderLevel(2, "talker")),
        filename_template="{talker}_{item:d}",
    )

    [recording] = resolve(tmp_path, layout).recordings

    assert recording.talkers == ["aa1"]
    assert recording.fields == {"dialect": "north", "item": "03"}


def test_different_talkers_from_folder_and_name_are_both_kept(tmp_path: Path):
    make_tree(tmp_path, ["sess/ab_cd.wav"])
    layout = ProjectLayout(
        levels=(FolderLevel(1, "speaker"),), filename_template="{talker}_{talker}"
    )

    [recording] = resolve(tmp_path, layout).recordings

    assert recording.talkers == ["sess", "ab", "cd"]


def test_levels_without_a_field_are_ignored(tmp_path: Path):
    make_tree(tmp_path, ["x/y/a.wav"])

    [recording] = resolve(
        tmp_path, ProjectLayout(levels=(FolderLevel(1, ""), FolderLevel(2, "talker")))
    ).recordings

    assert (recording.talkers, recording.fields) == (["y"], {})


def test_names_that_do_not_fit_the_template_are_reported(tmp_path: Path):
    make_tree(tmp_path, ["ab_01.wav", "odd.wav"])

    result = resolve(tmp_path, ProjectLayout(filename_template="{talker}_{n:d}"))

    assert result.report.template_mismatches == ["odd.wav"]
    assert [r.talkers for r in result.recordings] == [["ab"], []]


def test_talker_project_end_to_end(tmp_path: Path):
    talker_tree(tmp_path, annotated=3)
    layout = ProjectLayout(
        levels=(FolderLevel(1, "talker"),),
        data_files=(DataFileRole("trk", "", ".trk"), DataFileRole("pos", "", ".pos")),
    )

    result = resolve(tmp_path, layout)

    assert result.report.n_audio == 8
    assert result.report.n_annotated == 6
    assert len(result.report.unpaired_audio) == 2
    assert result.report.data_file_counts == {"trk": 8, "pos": 8}
    first = result.recordings[0]
    assert first.file_stem == "aa1/aa1_01"
    assert first.audio_file == "aa1/aa1_01.wav"
    assert first.talkers == ["aa1"]


def test_two_audio_files_with_one_stem_make_one_recording(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "a.WAV"])

    result = resolve(tmp_path, ProjectLayout())

    assert len(result.recordings) == 1


# --------------------------- several folders of annotations ---------------------------


def versions_tree(root: Path) -> Path:
    return make_tree(
        root,
        [
            "wav/a.wav",
            "wav/b.wav",
            "v1/a.TextGrid",
            "v1/b.TextGrid",
            "v2/a.TextGrid",
        ],
    )


def test_annotations_are_read_from_the_chosen_folder_only(tmp_path: Path):
    versions_tree(tmp_path)

    result = resolve(tmp_path, ProjectLayout(annotation_dir="v2"))

    assert {r.file_stem: r.annotation_file for r in result.recordings} == {
        "wav/a": "v2/a.TextGrid",
        "wav/b": None,
    }
    assert result.report.unpaired_annotations == []


def test_without_a_chosen_folder_the_first_annotation_found_is_used(tmp_path: Path):
    versions_tree(tmp_path)

    result = resolve(tmp_path, ProjectLayout())

    assert result.report.unpaired_annotations == ["v2/a.TextGrid"]


def test_a_chosen_folder_includes_the_folders_inside_it(tmp_path: Path):
    make_tree(
        tmp_path,
        ["wav/t1/a.wav", "labels/t1/a.TextGrid", "labelsold/t1/a.TextGrid"],
    )

    result = resolve(tmp_path, ProjectLayout(annotation_dir="labels"))

    assert result.recordings[0].annotation_file == "labels/t1/a.TextGrid"


def test_annotations_in_a_subfolder_are_paired_as_if_it_were_the_annotation_folder(
    tmp_path: Path,
):
    make_tree(
        tmp_path,
        [
            "wav/t1/a.wav",
            "wav/t2/a.wav",
            "ann/v1/t1/a.TextGrid",
            "ann/v2/t1/a.TextGrid",
            "ann/v2/t2/a.TextGrid",
        ],
    )

    result = resolve(tmp_path, ProjectLayout(annotation_dir="ann/v2"))

    assert {r.file_stem: r.annotation_file for r in result.recordings} == {
        "wav/t1/a": "ann/v2/t1/a.TextGrid",
        "wav/t2/a": "ann/v2/t2/a.TextGrid",
    }


# --------------------------- audio files that look like copies ---------------------------


def test_same_named_audio_of_the_same_size_in_another_folder_is_reported(
    tmp_path: Path,
):
    write_audio_like(tmp_path, "0_audio/a.wav", 10)
    write_audio_like(tmp_path, "work/a.wav", 10)
    write_audio_like(tmp_path, "0_audio/b.wav", 10)

    result = resolve(tmp_path, ProjectLayout())

    assert result.report.duplicate_audio == ["work/a.wav (same as 0_audio/a.wav)"]
    assert len(result.recordings) == 3  # nothing is left out


def test_same_names_of_different_sizes_are_not_reported(tmp_path: Path):
    write_audio_like(tmp_path, "t1/a.wav", 10)
    write_audio_like(tmp_path, "t2/a.wav", 12)

    assert resolve(tmp_path, ProjectLayout()).report.duplicate_audio == []


def test_empty_files_are_not_reported_as_copies(tmp_path: Path):
    make_tree(tmp_path, ["t1/a.wav", "t2/a.wav"])

    assert resolve(tmp_path, ProjectLayout()).report.duplicate_audio == []
