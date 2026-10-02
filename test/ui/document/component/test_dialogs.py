import pytest
from PyQt6.QtWidgets import QDialog, QMessageBox
from pytestqt.qtbot import QtBot

from ui.document.component.delete_channel_dialog import DeleteChannelDialog
from ui.document.component.paste_channel_dialog import PasteChannelDialog
from ui.document.component.paste_special_dialog import (
    PasteSpecialChoice,
    PasteSpecialDialog,
)


def click_button_with_text(monkeypatch: pytest.MonkeyPatch, text: str | None):
    """Make QMessageBox.exec 'click' the button labelled `text`
    (or none, to mimic cancelling)."""
    clicked: dict[str, object] = {}

    def fake_exec(self: QMessageBox) -> int:
        match = [b for b in self.buttons() if b.text() == text]
        clicked["button"] = match[0] if match else None
        return 0

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda self: clicked["button"])


def test_delete_channel_confirm_returns_true_when_delete_clicked(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    click_button_with_text(monkeypatch, "Delete")

    assert DeleteChannelDialog.confirm(None) is True


def test_delete_channel_confirm_returns_false_when_cancelled(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    click_button_with_text(monkeypatch, None)

    assert DeleteChannelDialog.confirm(None) is False


@pytest.mark.parametrize(
    ("text", "expected"),
    [("Left Channel", 0), ("Right Channel", 1), (None, None)],
)
def test_paste_channel_dialog_returns_chosen_channel(
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
    text: str | None,
    expected: int | None,
):
    click_button_with_text(monkeypatch, text)

    assert PasteChannelDialog.get_channel(None, is_clip_stereo=False) == expected


def test_paste_channel_dialog_message_depends_on_clip_channels(qtbot: QtBot):
    dlg = PasteChannelDialog()

    assert "clip is stereo" in dlg._get_message(True)
    assert "clip is mono" in dlg._get_message(False)


def test_paste_special_dialog_defaults(qtbot: QtBot):
    dlg = PasteSpecialDialog()
    qtbot.addWidget(dlg)

    assert dlg.choice() == PasteSpecialChoice(new_channel_idx=1, insert_silence=True)


def test_paste_special_dialog_reflects_selected_options(qtbot: QtBot):
    dlg = PasteSpecialDialog()
    qtbot.addWidget(dlg)

    dlg.channel_button_group.button(0).setChecked(True)
    dlg.without_silence_radio.setChecked(True)

    assert dlg.choice() == PasteSpecialChoice(new_channel_idx=0, insert_silence=False)


def test_paste_special_get_choice_returns_choice_when_accepted(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        PasteSpecialDialog, "exec", lambda self: QDialog.DialogCode.Accepted
    )

    assert PasteSpecialDialog.get_choice(None) == PasteSpecialChoice(1, True)


def test_paste_special_get_choice_returns_none_when_rejected(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        PasteSpecialDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )

    assert PasteSpecialDialog.get_choice(None) is None
