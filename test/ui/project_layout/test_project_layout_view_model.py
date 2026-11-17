from pathlib import Path

import pytest
from support.audio_files import textgrid_with_tiers
from support.project_tree import make_tree, talker_tree, write_audio_like
from support.view_models import make_project_layout_view_model

from core.project_layout.entity.project_layout import FolderLevel
from core.project_layout.project_layout_file import LoadProjectLayout
from ui.project_layout.project_layout_view_model import ProjectLayoutViewModel
from ui.project_layout.state.project_layout_state import ProjectLayoutState


def prepared(
    root: Path,
) -> tuple[ProjectLayoutViewModel, list[ProjectLayoutState]]:
    view_model = make_project_layout_view_model(str(root))
    states: list[ProjectLayoutState] = []
    view_model.subscribe(states.append)
    view_model.prepare()
    return view_model, states


def test_flat_project_of_paired_files_needs_no_review(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "a.TextGrid", "b.wav", "b.TextGrid"])

    view_model, _ = prepared(tmp_path)

    assert view_model.needs_review is False


def test_unpaired_audio_needs_review(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "a.TextGrid", "b.wav"])

    view_model, states = prepared(tmp_path)

    assert view_model.needs_review is True
    assert (states[-1].n_unpaired_audio, states[-1].unpaired_audio_examples) == (
        1,
        ["b.wav"],
    )


def test_project_with_folders_needs_review_and_suggests_talker(tmp_path: Path):
    talker_tree(tmp_path)

    view_model, states = prepared(tmp_path)

    state = states[-1]
    assert view_model.needs_review is True
    assert [(l.depth, l.n_values, l.field) for l in state.levels] == [(1, 2, "talker")]
    assert sorted(r.name for r in state.roles) == ["pos", "trk"]
    assert all(r.selected for r in state.roles)
    assert state.n_recordings == 8


def test_leaving_out_unpaired_audio_changes_what_is_imported(tmp_path: Path):
    talker_tree(tmp_path, annotated=2)
    view_model, states = prepared(tmp_path)

    view_model.set_include_unpaired_audio(False)

    assert states[-1].n_recordings == 4
    assert states[-1].n_unpaired_audio == 4
    assert states[-1].include_unpaired_audio is False


def test_deselecting_a_data_file_kind_removes_its_column(tmp_path: Path):
    talker_tree(tmp_path)
    view_model, states = prepared(tmp_path)
    index = [r.name for r in states[-1].roles].index("pos")

    view_model.set_role_selected(index, False)

    assert "pos" not in states[-1].preview_headers
    assert "trk" in states[-1].preview_headers


def test_renaming_a_data_file_kind(tmp_path: Path):
    talker_tree(tmp_path)
    view_model, states = prepared(tmp_path)
    index = [r.name for r in states[-1].roles].index("pos")

    view_model.set_role_name(index, "position")

    assert "position" in states[-1].preview_headers


def test_changing_a_level_meaning_changes_the_preview(tmp_path: Path):
    talker_tree(tmp_path)
    view_model, states = prepared(tmp_path)

    view_model.set_level_field(1, "condition")

    assert "condition" in states[-1].preview_headers
    assert states[-1].preview_rows[0][1] == ""  # no talkers any more


def test_filename_template_adds_fields_to_the_preview(tmp_path: Path):
    talker_tree(tmp_path)
    view_model, states = prepared(tmp_path)

    view_model.set_filename_template("{*}_{item:d}")

    assert states[-1].template_error == ""
    assert "item" in states[-1].preview_headers
    assert states[-1].preview_rows[0][states[-1].preview_headers.index("item")] == "01"


def test_invalid_template_is_reported_and_blocks_import(tmp_path: Path):
    talker_tree(tmp_path)
    view_model, states = prepared(tmp_path)

    view_model.set_filename_template("{oops")

    assert states[-1].template_error != ""
    assert states[-1].can_import is False


def test_names_that_do_not_fit_are_counted(tmp_path: Path):
    make_tree(tmp_path, ["ab_01.wav", "odd.wav"])
    view_model, states = prepared(tmp_path)

    view_model.set_filename_template("{talker}_{n:d}")

    assert states[-1].n_template_mismatches == 1
    assert states[-1].template_mismatch_examples == ["odd.wav"]


def test_saving_writes_the_layout_to_the_project_file(tmp_path: Path):
    talker_tree(tmp_path, annotated=2)
    view_model, _ = prepared(tmp_path)

    view_model.save_project_layout()

    saved = LoadProjectLayout()(str(tmp_path))
    assert saved is not None and saved.levels == (FolderLevel(1, "talker"),)
    assert sorted(r.name for r in saved.data_files) == ["pos", "trk"]
    assert view_model.has_saved_layout is True


def test_an_unusable_template_is_not_saved(tmp_path: Path):
    talker_tree(tmp_path)
    view_model, _ = prepared(tmp_path)
    view_model.set_filename_template("{oops")

    with pytest.raises(ValueError):
        view_model.save_project_layout()

    assert LoadProjectLayout()(str(tmp_path)) is None


def test_second_import_uses_the_saved_layout_without_review(tmp_path: Path):
    talker_tree(tmp_path)
    first, _ = prepared(tmp_path)
    first.set_level_field(1, "group")
    first.set_include_unpaired_audio(False)
    first.save_project_layout()

    second, states = prepared(tmp_path)

    assert second.has_saved_layout is True
    assert second.needs_review is False
    assert [l.field for l in states[-1].levels] == ["group"]
    assert states[-1].include_unpaired_audio is False
    assert sorted(r.name for r in states[-1].roles if r.selected) == ["pos", "trk"]


def test_saved_layout_keeps_the_names_given_to_data_files(tmp_path: Path):
    talker_tree(tmp_path)
    first, states = prepared(tmp_path)
    first.set_role_name([r.name for r in states[-1].roles].index("pos"), "position")
    first.save_project_layout()

    _, states = prepared(tmp_path)

    assert "position" in [r.name for r in states[-1].roles]


def test_saved_layout_asks_again_when_names_stop_fitting_the_template(tmp_path: Path):
    make_tree(tmp_path, ["ab_01.wav"])
    first, _ = prepared(tmp_path)
    first.set_filename_template("{talker}_{n:d}")
    first.save_project_layout()
    make_tree(tmp_path, ["strange.wav"])

    second, _ = prepared(tmp_path)

    assert second.needs_review is True


def test_project_without_audio_cannot_be_imported(tmp_path: Path):
    make_tree(tmp_path, ["notes.txt"])

    view_model, states = prepared(tmp_path)

    assert states[-1].can_import is False
    assert view_model.needs_review is True


# --------------------------- recordings stored as one file per channel ---------------------------


def channel_project(root: Path) -> Path:
    """Two recordings, each a pair of mono files that could be channels or takes"""
    make_tree(
        root,
        [
            "a_L.wav",
            "a_R.wav",
            "a.TextGrid",
            "b_L.wav",
            "b_R.wav",
            "b.TextGrid",
            "a.trk",
            "b.trk",
        ],
    )
    (root / "a.TextGrid").write_text(
        textgrid_with_tiers(["Ann - words", "Bob - words"])
    )
    return root


def test_unclear_channels_are_offered_not_assumed(tmp_path: Path):
    channel_project(tmp_path)

    view_model, states = prepared(tmp_path)

    state = states[-1]
    assert view_model.needs_review is True
    assert state.channel_candidate is not None
    assert state.channel_candidate.n_groups == 2
    assert state.channels_enabled is False
    assert [c.label for c in state.channels] == ["L", "R"]
    assert state.n_audio == 4


def test_choosing_channels_combines_the_files_and_finds_the_rest(tmp_path: Path):
    channel_project(tmp_path)
    view_model, states = prepared(tmp_path)

    view_model.set_channels_enabled(True)

    state = states[-1]
    assert state.channels_enabled is True
    assert (state.n_audio, state.n_audio_files, state.n_recordings) == (2, 4, 2)
    assert state.n_annotated == 2
    assert [r.name for r in state.roles] == ["trk"]
    assert state.roles[0].selected is True


def test_talker_names_are_taken_from_the_tiers_of_an_annotation(tmp_path: Path):
    channel_project(tmp_path)
    view_model, states = prepared(tmp_path)

    view_model.set_channels_enabled(True)

    state = states[-1]
    assert state.talker_names == ["Ann", "Bob"]
    assert [c.talker for c in state.channels] == ["Ann", "Bob"]
    assert states[-1].preview_rows[0][1] == "Ann, Bob"


def test_talker_names_are_not_guessed_when_they_do_not_fit_the_channels(
    tmp_path: Path,
):
    channel_project(tmp_path)
    (tmp_path / "a.TextGrid").write_text(
        textgrid_with_tiers(["Ann - words", "Bob - words", "Cy - words"])
    )
    view_model, states = prepared(tmp_path)

    view_model.set_channels_enabled(True)

    assert [c.talker for c in states[-1].channels] == ["", ""]
    assert states[-1].talker_names == ["Ann", "Bob", "Cy"]


def test_the_user_can_name_the_talker_on_each_channel(tmp_path: Path):
    channel_project(tmp_path)
    view_model, states = prepared(tmp_path)
    view_model.set_channels_enabled(True)

    view_model.set_channel_talker(0, "Dee")
    view_model.set_channel_talker(1, "Eli")

    assert [c.talker for c in states[-1].channels] == ["Dee", "Eli"]
    assert states[-1].preview_rows[0][1] == "Dee, Eli"


def test_saving_channels_keeps_the_talker_names(tmp_path: Path):
    channel_project(tmp_path)
    view_model, _ = prepared(tmp_path)
    view_model.set_channels_enabled(True)

    view_model.save_project_layout()

    saved = LoadProjectLayout()(str(tmp_path))
    assert saved is not None
    assert [(c.label, c.talker) for c in saved.channels] == [("L", "Ann"), ("R", "Bob")]


def test_saved_channels_are_used_on_the_next_import(tmp_path: Path):
    channel_project(tmp_path)
    first, _ = prepared(tmp_path)
    first.set_channels_enabled(True)
    first.set_channel_talker(0, "Dee")
    first.save_project_layout()

    second, states = prepared(tmp_path)

    assert second.needs_review is False
    assert states[-1].channels_enabled is True
    assert states[-1].n_recordings == 2
    assert [c.talker for c in states[-1].channels] == ["Dee", "Bob"]


def test_turning_channels_off_again_restores_separate_recordings(tmp_path: Path):
    channel_project(tmp_path)
    view_model, states = prepared(tmp_path)
    view_model.set_channels_enabled(True)

    view_model.set_channels_enabled(False)

    assert (states[-1].n_audio, states[-1].channels_enabled) == (4, False)


def test_talkers_named_from_the_tiers_replace_a_guessed_talker_folder(tmp_path: Path):
    make_tree(
        tmp_path,
        [
            "d1/d1_L.wav",
            "d1/d1_R.wav",
            "d1/d1.TextGrid",
            "d2/d2_L.wav",
            "d2/d2_R.wav",
            "d2/d2.TextGrid",
        ],
    )
    (tmp_path / "d1/d1.TextGrid").write_text(
        textgrid_with_tiers(["Ann - words", "Bob - words"])
    )
    view_model, states = prepared(tmp_path)
    assert states[-1].levels[0].field == "talker"  # the folder looks like a talker

    view_model.set_channels_enabled(True)

    assert states[-1].levels[0].field == ""
    assert states[-1].preview_rows[0][1] == "Ann, Bob"


# --------------------------- annotations kept in several folders ---------------------------


def versions_project(root: Path) -> Path:
    return make_tree(
        root,
        ["wav/a.wav", "wav/b.wav", "v1/a.TextGrid", "v1/b.TextGrid", "v2/a.TextGrid"],
    )


def test_folders_holding_versions_of_the_annotations_are_offered(tmp_path: Path):
    versions_project(tmp_path)

    view_model, states = prepared(tmp_path)

    state = states[-1]
    assert view_model.needs_review is True
    assert [f.folder for f in state.annotation_folders] == ["v1", "v2"]
    assert state.annotation_folders_overlap is True
    assert (state.annotation_dir, state.n_annotated) == ("v1", 2)
    assert state.n_unpaired_annotations == 0


def test_the_user_chooses_the_folder_the_annotations_are_read_from(tmp_path: Path):
    versions_project(tmp_path)
    view_model, states = prepared(tmp_path)

    view_model.set_annotation_dir("v2")

    assert (states[-1].annotation_dir, states[-1].n_annotated) == ("v2", 1)
    assert states[-1].preview_rows[0][
        states[-1].preview_headers.index("Annotation")
    ] == ("v2/a.TextGrid")


def test_the_chosen_folder_is_saved_and_used_next_time(tmp_path: Path):
    versions_project(tmp_path)
    first, _ = prepared(tmp_path)
    first.set_annotation_dir("v2")
    first.save_project_layout()

    second, states = prepared(tmp_path)

    assert second.needs_review is False
    assert (states[-1].annotation_dir, states[-1].n_annotated) == ("v2", 1)
    assert LoadProjectLayout()(str(tmp_path)).annotation_dir == "v2"  # type: ignore[union-attr]


def test_folders_of_different_recordings_are_not_a_question(tmp_path: Path):
    make_tree(tmp_path, ["a/x.wav", "a/x.TextGrid", "b/y.wav", "b/y.TextGrid"])

    _, states = prepared(tmp_path)

    assert states[-1].annotation_folders_overlap is False
    assert states[-1].annotation_dir == ""


def test_the_preview_shows_recordings_with_annotations_first(tmp_path: Path):
    paths = [f"r{n:02d}.wav" for n in range(30)] + ["r29.TextGrid"]
    make_tree(tmp_path, paths)

    _, states = prepared(tmp_path)

    state = states[-1]
    annotation = state.preview_headers.index("Annotation")
    assert state.preview_rows[0][0] == "r29"
    assert state.preview_rows[0][annotation] == "r29.TextGrid"
    assert state.preview_rows[1][annotation] == "—"


def test_the_preview_names_audio_files_with_their_folders(tmp_path: Path):
    make_tree(tmp_path, ["0_audio/a.wav", "labels/a.TextGrid"])

    _, states = prepared(tmp_path)

    state = states[-1]
    assert state.preview_rows[0][state.preview_headers.index("Audio")] == (
        "0_audio/a.wav"
    )


def test_audio_that_looks_like_a_copy_is_warned_about_and_reviewed(tmp_path: Path):
    write_audio_like(tmp_path, "0_audio/a.wav", 10)
    write_audio_like(tmp_path, "work/a.wav", 10)

    view_model, states = prepared(tmp_path)

    assert view_model.needs_review is True
    assert states[-1].n_duplicate_audio == 1
    assert states[-1].duplicate_audio_examples == ["work/a.wav (same as 0_audio/a.wav)"]
