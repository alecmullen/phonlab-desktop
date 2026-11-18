import pytest
from PyQt6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox
from pytestqt.qtbot import QtBot

from ui.annotation.component.add_tiers_dialog import AddTiersDialog


def make_dialog(
    qtbot: QtBot, available: list[str], existing: list[str] | None = None
) -> AddTiersDialog:
    dialog = AddTiersDialog(available, existing or [])
    qtbot.addWidget(dialog)
    return dialog


def ok_enabled(dialog: AddTiersDialog) -> bool:
    return dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()


def option(dialog: AddTiersDialog, name: str) -> QCheckBox:
    return next(c for c in dialog.option_checks if c.text() == name)


def test_offers_every_tier_name_in_the_database_as_a_checkbox(qtbot: QtBot):
    dialog = make_dialog(qtbot, ["break", "phone", "word"])

    assert [c.text() for c in dialog.option_checks] == ["break", "phone", "word"]
    assert not any(c.isChecked() for c in dialog.option_checks)


def test_nothing_chosen_means_nothing_to_add_and_ok_is_disabled(qtbot: QtBot):
    dialog = make_dialog(qtbot, ["word"])

    assert dialog.names() == []
    assert not ok_enabled(dialog)


def test_ticked_names_are_returned_in_list_order(qtbot: QtBot):
    dialog = make_dialog(qtbot, ["break", "phone", "word"])

    option(dialog, "word").setChecked(True)
    option(dialog, "break").setChecked(True)

    assert dialog.names() == ["break", "word"]
    assert ok_enabled(dialog)


def test_tiers_the_file_already_has_are_shown_ticked_and_cannot_be_changed(
    qtbot: QtBot,
):
    dialog = make_dialog(qtbot, ["phone", "word"], existing=["word"])

    word = option(dialog, "word")
    assert word.isChecked() and not word.isEnabled()
    assert dialog.names() == []  # an existing tier is not added again


def test_new_tier_is_returned_after_the_ticked_names(qtbot: QtBot):
    dialog = make_dialog(qtbot, ["word"])
    option(dialog, "word").setChecked(True)

    dialog.new_check.setChecked(True)
    dialog.new_edit.setText("  tone  ")

    assert dialog.names() == ["word", "tone"]
    assert ok_enabled(dialog)


def test_typing_a_new_name_ticks_the_new_tier_box(qtbot: QtBot):
    dialog = make_dialog(qtbot, ["word"])

    qtbot.keyClicks(dialog.new_edit, "tone")

    assert dialog.new_check.isChecked()
    assert dialog.names() == ["tone"]
    assert ok_enabled(dialog)


def test_a_ticked_new_tier_needs_a_name(qtbot: QtBot):
    dialog = make_dialog(qtbot, ["word"])
    option(dialog, "word").setChecked(True)

    dialog.new_check.setChecked(True)

    assert dialog.problem() is not None
    assert dialog.hint.text() != ""
    assert not ok_enabled(dialog)


def test_a_blank_new_name_is_not_a_name(qtbot: QtBot):
    dialog = make_dialog(qtbot, [])
    dialog.new_check.setChecked(True)

    dialog.new_edit.setText("   ")

    assert not ok_enabled(dialog)


def test_a_new_name_the_file_already_has_is_refused(qtbot: QtBot):
    dialog = make_dialog(qtbot, ["word"], existing=["word"])

    dialog.new_edit.setText("word")
    dialog.new_check.setChecked(True)

    assert "word" in (dialog.problem() or "")
    assert not ok_enabled(dialog)


def test_a_new_name_that_is_also_ticked_in_the_list_is_refused(qtbot: QtBot):
    dialog = make_dialog(qtbot, ["word"])
    option(dialog, "word").setChecked(True)

    dialog.new_check.setChecked(True)
    dialog.new_edit.setText("word")

    assert dialog.problem() is not None
    assert not ok_enabled(dialog)


def test_a_new_name_differing_only_in_case_is_allowed(qtbot: QtBot):
    dialog = make_dialog(qtbot, ["word"], existing=["word"])

    dialog.new_check.setChecked(True)
    dialog.new_edit.setText("Word")

    assert dialog.problem() is None
    assert ok_enabled(dialog)


def test_unticking_the_new_tier_box_drops_the_new_name(qtbot: QtBot):
    dialog = make_dialog(qtbot, ["word"])
    option(dialog, "word").setChecked(True)
    dialog.new_edit.setText("tone")
    dialog.new_check.setChecked(True)

    dialog.new_check.setChecked(False)

    assert dialog.names() == ["word"]


def test_a_database_with_no_tiers_yet_still_lets_the_user_add_a_new_one(qtbot: QtBot):
    dialog = make_dialog(qtbot, [])
    assert dialog.option_checks == []

    dialog.new_edit.setText("word")
    dialog.new_check.setChecked(True)

    assert dialog.names() == ["word"]
    assert ok_enabled(dialog)


def test_get_names_returns_the_choice_when_accepted(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    def accept(self: AddTiersDialog) -> QDialog.DialogCode:
        option(self, "word").setChecked(True)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(AddTiersDialog, "exec", accept)

    assert AddTiersDialog.get_names(["word"], []) == ["word"]


def test_get_names_returns_none_when_cancelled(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        AddTiersDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )

    assert AddTiersDialog.get_names(["word"], []) is None
