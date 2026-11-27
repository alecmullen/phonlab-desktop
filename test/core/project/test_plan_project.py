from pathlib import Path

from support.project_tree import make_tree, talker_tree

from core.project.scan_project_files import plan_project
from core.project_layout.project_layout_file import SaveProjectLayout
from phonlab_project.layout.project_layout import FolderLevel, ProjectLayout


def test_a_project_that_reads_cleanly_has_no_problems(tmp_path: Path):
    talker_tree(tmp_path)

    plan = plan_project(str(tmp_path))

    assert plan.problems == []
    assert plan.layout_source == "inferred"
    assert len(plan.recordings) == 8
    assert plan.report.n_annotated == 8


def test_the_layout_comes_from_the_one_given_else_the_saved_one(tmp_path: Path):
    talker_tree(tmp_path)
    given = ProjectLayout(levels=(FolderLevel(1, "group"),))

    assert plan_project(str(tmp_path), given).layout_source == "given"
    assert plan_project(str(tmp_path), given).recordings[0].fields == {"group": "aa1"}

    SaveProjectLayout()(str(tmp_path), given)
    assert plan_project(str(tmp_path)).layout_source == "saved"


def test_an_annotation_file_that_belongs_to_no_sound_file_is_a_problem(
    tmp_path: Path,
):
    make_tree(tmp_path, ["a.wav", "a.TextGrid", "orphan.TextGrid"])

    plan = plan_project(str(tmp_path))

    assert [p for p in plan.problems if "orphan.TextGrid" in p]
    assert "belong to no sound file" in plan.problems[0]


def test_sound_files_that_do_not_fit_the_filename_template_are_a_problem(
    tmp_path: Path,
):
    make_tree(tmp_path, ["aa1_01.wav", "odd.wav"])

    plan = plan_project(
        str(tmp_path),
        ProjectLayout(filename_template="{talker}_{item:d}", annotation_ext=None),
    )

    assert plan.problems == [
        "1 sound files do not fit the filename template (for example odd.wav)"
    ]


def test_a_filename_template_that_cannot_be_used_is_a_problem(tmp_path: Path):
    make_tree(tmp_path, ["a.wav"])

    plan = plan_project(str(tmp_path), ProjectLayout(filename_template="{oops"))

    assert plan.template_unusable
    assert "the filename template cannot be used" in plan.problems


def test_copies_of_sound_files_are_a_problem(tmp_path: Path):
    for folder in ("one", "two"):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "a.wav").write_bytes(b"same sound")

    plan = plan_project(str(tmp_path))

    assert "look like copies" in " ".join(plan.problems)


def test_a_folder_with_no_sound_files_is_a_problem(tmp_path: Path):
    assert plan_project(str(tmp_path)).problems == ["no sound files were found"]


def test_the_plan_describes_itself_and_what_needs_a_look(tmp_path: Path):
    make_tree(tmp_path, ["aa1/a.wav", "aa1/a.TextGrid", "orphan.TextGrid"])

    text = str(plan_project(str(tmp_path)))

    assert "Layout: inferred" in text
    assert "1 recordings, 1 with an annotation (.textgrid)" in text
    assert "aa1/a" in text
    assert "Needs a look: 1 annotation files belong to no sound file" in text


def test_sound_files_named_like_channels_that_cannot_be_read_are_a_problem(
    tmp_path: Path,
):
    make_tree(tmp_path, ["a_L.wav", "a_R.wav"])

    plan = plan_project(str(tmp_path))

    assert "named like the channels of one recording" in plan.problems[0]
