from pathlib import Path

from PyQt6.QtWidgets import QDialog
from pytestqt.qtbot import QtBot
from support.audio_files import textgrid_with_tiers
from support.project_tree import make_tree, talker_tree
from support.view_models import make_project_layout_view_model

from ui.project_layout.project_layout_dialog import ProjectLayoutDialog


def make_dialog(qtbot: QtBot, root: Path) -> ProjectLayoutDialog:
    view_model = make_project_layout_view_model(str(root))
    view_model.prepare()
    dialog = ProjectLayoutDialog(view_model)
    qtbot.addWidget(dialog)
    return dialog


def test_dialog_summarizes_the_project(qtbot: QtBot, tmp_path: Path):
    talker_tree(tmp_path, annotated=2)

    dialog = make_dialog(qtbot, tmp_path)

    assert "8 audio files" in dialog.summary_label.text()
    assert "4 audio files have no annotation" in dialog.unpaired_audio_label.text()
    assert dialog.preview_table.rowCount() == 8


def test_leave_out_checkbox_updates_the_import(qtbot: QtBot, tmp_path: Path):
    talker_tree(tmp_path, annotated=2)
    dialog = make_dialog(qtbot, tmp_path)

    dialog.leave_out_check.setChecked(True)

    assert dialog.view_model.resolved.report.n_recordings == 4
    assert dialog.preview_table.rowCount() == 4


def test_leave_out_checkbox_is_disabled_when_everything_is_paired(
    qtbot: QtBot, tmp_path: Path
):
    talker_tree(tmp_path)

    dialog = make_dialog(qtbot, tmp_path)

    assert dialog.leave_out_check.isEnabled() is False


def test_folder_level_edit_changes_the_variable_name(qtbot: QtBot, tmp_path: Path):
    talker_tree(tmp_path)
    dialog = make_dialog(qtbot, tmp_path)
    edit = dialog.levels_group.findChildren(type(dialog.template_edit))[0]

    edit.setText("condition")
    edit.editingFinished.emit()

    assert "condition" in dialog.state.preview_headers


def test_template_typed_by_the_user_is_applied(qtbot: QtBot, tmp_path: Path):
    talker_tree(tmp_path)
    dialog = make_dialog(qtbot, tmp_path)

    qtbot.keyClicks(dialog.template_edit, "{*}_{item:d}")

    assert "item" in dialog.state.preview_headers
    assert dialog.template_status.text() == ""


def test_invalid_template_disables_import_and_shows_the_error(
    qtbot: QtBot, tmp_path: Path
):
    talker_tree(tmp_path)
    dialog = make_dialog(qtbot, tmp_path)

    qtbot.keyClicks(dialog.template_edit, "{oops")

    assert dialog.template_status.text() != ""
    assert dialog.import_button is not None
    assert dialog.import_button.isEnabled() is False


def test_accepting_saves_the_layout(qtbot: QtBot, tmp_path: Path):
    talker_tree(tmp_path, annotated=2)
    dialog = make_dialog(qtbot, tmp_path)

    dialog.accept_layout()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert "[import]" in (tmp_path / "phonlab.toml").read_text()


def test_review_asks_nothing_of_a_project_that_needs_no_decisions(
    qtbot: QtBot, tmp_path: Path
):
    make_tree(tmp_path, ["a.wav", "a.TextGrid"])
    view_model = make_project_layout_view_model(str(tmp_path))

    assert ProjectLayoutDialog.review_layout(view_model) is True

    assert "[import]" in (tmp_path / "phonlab.toml").read_text()


def test_data_file_kinds_are_listed_with_counts(qtbot: QtBot, tmp_path: Path):
    talker_tree(tmp_path)

    dialog = make_dialog(qtbot, tmp_path)

    assert [r.n_files for r in dialog.state.roles] == [8, 8]


def test_channels_group_offers_the_sets_and_talker_names(qtbot: QtBot, tmp_path: Path):
    make_tree(tmp_path, ["a_L.wav", "a_R.wav", "b_L.wav", "b_R.wav", "a.TextGrid"])
    (tmp_path / "a.TextGrid").write_text(
        textgrid_with_tiers(["Ann - words", "Bob - words"])
    )
    dialog = make_dialog(qtbot, tmp_path)

    assert dialog.channels_group.isHidden() is False
    assert dialog.channels_check.isChecked() is False
    assert dialog.channels_table.isEnabled() is False

    dialog.channels_check.setChecked(True)

    assert dialog.channels_table.isEnabled() is True
    assert dialog.view_model.resolved.report.n_audio == 2
    assert [combo.currentText() for combo in dialog.talker_combos] == ["Ann", "Bob"]
    assert [
        dialog.talker_combos[0].itemText(i)
        for i in range(dialog.talker_combos[0].count())
    ] == ["", "Ann", "Bob"]


def test_typing_a_talker_name_for_a_channel(qtbot: QtBot, tmp_path: Path):
    make_tree(tmp_path, ["a_L.wav", "a_R.wav", "b_L.wav", "b_R.wav"])
    dialog = make_dialog(qtbot, tmp_path)
    dialog.channels_check.setChecked(True)

    dialog.talker_combos[1].setEditText("Zed")
    dialog.talker_combos[1].lineEdit().editingFinished.emit()

    assert dialog.view_model.channel_roles[1].talker == "Zed"


def test_projects_without_channel_sets_hide_the_channels_group(
    qtbot: QtBot, tmp_path: Path
):
    talker_tree(tmp_path)

    dialog = make_dialog(qtbot, tmp_path)

    assert dialog.channels_group.isHidden() is True
