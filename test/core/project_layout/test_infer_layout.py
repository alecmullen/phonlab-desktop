from pathlib import Path

from support.project_tree import make_tree, talker_tree

from core.project_layout.entity.import_report import LayoutSuggestion
from core.project_layout.entity.project_layout import DataFileRole, FolderLevel
from core.project_layout.infer_layout import InferLayout
from core.project_layout.scan_project_tree import ScanProjectTree


def infer(root: Path) -> LayoutSuggestion:
    return InferLayout()(ScanProjectTree()(str(root)))


def test_flat_textgrid_project_needs_no_decisions(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "a.TextGrid", "b.wav", "b.TextGrid"])

    suggestion = infer(tmp_path)

    assert suggestion.layout.annotation_ext == ".textgrid"
    assert suggestion.layout.levels == ()
    assert suggestion.data_file_candidates == []


def test_annotation_format_is_the_one_paired_with_most_audio(tmp_path: Path):
    make_tree(
        tmp_path,
        [
            "a.wav",
            "a.words",
            "a.phones",
            "b.wav",
            "b.words",
            "b.phones",
            "c.wav",
            "c.TextGrid",
        ],
    )

    suggestion = infer(tmp_path)

    assert suggestion.layout.annotation_ext == ".words"
    assert suggestion.annotation_sources[".textgrid"].n_paired == 1


def test_elan_files_are_annotations(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "a.eaf", "b.wav", "b.eaf"])

    suggestion = infer(tmp_path)

    assert suggestion.layout.annotation_ext == ".eaf"
    assert suggestion.data_file_candidates == []


def test_subtitle_files_are_annotations(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "a.srt", "b.wav", "b.srt"])

    suggestion = infer(tmp_path)

    assert suggestion.layout.annotation_ext == ".srt"
    assert suggestion.data_file_candidates == []


def test_companions_of_the_annotation_format_are_not_data_files(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "a.wrd", "a.phn", "a.trk"])

    suggestion = infer(tmp_path)

    assert [c.role.ext for c in suggestion.data_file_candidates] == [".trk"]


def test_no_annotation_files_gives_no_annotation_format(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "b.wav"])

    assert infer(tmp_path).layout.annotation_ext is None


def test_data_file_kinds_with_enough_coverage_are_selected(tmp_path: Path):
    paths = [f"r{n}.wav" for n in range(10)]
    paths += [f"r{n}.trk" for n in range(10)]  # every recording
    paths += [f"r{n}_pitch.txt" for n in range(2)]  # a few
    make_tree(tmp_path, paths)

    suggestion = infer(tmp_path)

    by_name = {c.role.name: c for c in suggestion.data_file_candidates}
    assert set(by_name) == {"trk", "pitch_txt"}
    assert by_name["trk"].coverage == 1.0
    assert by_name["pitch_txt"].n_files == 2
    assert suggestion.layout.data_files == (DataFileRole("trk", "", ".trk"),)


def test_unrelated_files_are_not_data_files(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "readme.txt", "table.csv"])

    assert infer(tmp_path).data_file_candidates == []


def test_deepest_varying_folder_level_is_guessed_to_be_the_talker(tmp_path: Path):
    make_tree(
        tmp_path,
        [
            "train/dr1/m1/s1.wav",
            "train/dr1/f2/s1.wav",
            "train/dr2/m3/s1.wav",
            "test/dr1/f4/s1.wav",
        ],
    )

    suggestion = infer(tmp_path)

    assert suggestion.layout.levels == (
        FolderLevel(1, ""),
        FolderLevel(2, ""),
        FolderLevel(3, "talker"),
    )
    assert [s.n_values for s in suggestion.levels] == [2, 2, 4]


def test_folder_name_at_start_of_file_names_marks_the_talker_level(tmp_path: Path):
    make_tree(
        tmp_path,
        ["g1/x1/x1_a.wav", "g1/y2/y2_a.wav", "g2/z3/z3_a.wav", "g2/w4/w4_a.wav"],
    )

    suggestion = infer(tmp_path)

    assert suggestion.levels[1].name_prefix_share == 1.0
    assert suggestion.layout.levels[1] == FolderLevel(2, "talker")


def test_single_folder_for_everything_is_not_a_talker(tmp_path: Path):
    make_tree(tmp_path, ["audio/a.wav", "audio/b.wav"])

    assert infer(tmp_path).layout.levels == (FolderLevel(1, ""),)


def test_project_with_talker_folders(tmp_path: Path):
    talker_tree(tmp_path, annotated=2)

    suggestion = infer(tmp_path)

    assert suggestion.layout.levels == (FolderLevel(1, "talker"),)
    assert sorted(c.role.name for c in suggestion.data_file_candidates) == [
        "pos",
        "trk",
    ]
    assert len(suggestion.layout.data_files) == 2


# --------------------------- several folders of annotations ---------------------------


def test_folders_with_annotations_of_the_same_recordings_are_offered(tmp_path: Path):
    make_tree(
        tmp_path,
        ["wav/a.wav", "wav/b.wav", "v1/a.TextGrid", "v1/b.TextGrid", "v2/a.TextGrid"],
    )

    suggestion = infer(tmp_path)

    sources = suggestion.annotation_sources[".textgrid"]
    assert sources.overlapping is True
    assert [(f.folder, f.n_files) for f in sources.folders] == [("v1", 2), ("v2", 1)]
    assert suggestion.layout.annotation_dir == "v1"  # the one with most annotations


def test_folders_of_different_recordings_are_not_a_choice(tmp_path: Path):
    make_tree(
        tmp_path,
        ["a/x.wav", "a/x.TextGrid", "b/y.wav", "b/y.TextGrid"],
    )

    suggestion = infer(tmp_path)

    assert suggestion.annotation_sources[".textgrid"].overlapping is False
    assert suggestion.layout.annotation_dir == ""


def test_subfolders_are_offered_when_the_top_folder_holds_all_the_versions(
    tmp_path: Path,
):
    make_tree(
        tmp_path,
        [
            "wav/a.wav",
            "wav/b.wav",
            "ann/v1/a.TextGrid",
            "ann/v1/b.TextGrid",
            "ann/v2/a.TextGrid",
        ],
    )

    suggestion = infer(tmp_path)

    sources = suggestion.annotation_sources[".textgrid"]
    assert [(f.folder, f.n_files, f.n_paired) for f in sources.folders] == [
        ("ann/v1", 2, 2),
        ("ann/v2", 1, 1),
    ]
    assert sources.overlapping is True
    assert suggestion.layout.annotation_dir == "ann/v1"


def test_annotations_next_to_the_audio_and_in_a_folder_are_all_counted(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "a.TextGrid", "b.wav", "labels/b.TextGrid"])

    suggestion = infer(tmp_path)

    assert suggestion.annotation_sources[".textgrid"].n_paired == 2
