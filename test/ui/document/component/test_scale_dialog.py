import pytest
from PyQt6.QtWidgets import QDialog, QDialogButtonBox
from pytestqt.qtbot import QtBot

from ui.document.component.scale_dialog import DEFAULT_SCALE_DBFS, ScaleAudioDialog


def test_default_scale(qtbot: QtBot):
    dialog = ScaleAudioDialog()
    qtbot.addWidget(dialog)

    assert dialog.get_scale() == DEFAULT_SCALE_DBFS


def test_get_scale_parses_entered_number(qtbot: QtBot):
    dialog = ScaleAudioDialog(applies_to_selection=True)
    qtbot.addWidget(dialog)

    dialog.scale_edit.setText("-3.5")

    assert dialog.get_scale() == -3.5


def test_ok_disabled_for_invalid_input(qtbot: QtBot):
    dialog = ScaleAudioDialog()
    qtbot.addWidget(dialog)
    ok = dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)

    dialog.scale_edit.setText("")
    assert not ok.isEnabled()
    dialog.scale_edit.setText("-")
    assert not ok.isEnabled()
    dialog.scale_edit.setText("-2")
    assert ok.isEnabled()


def test_get_scale_value_returns_none_when_cancelled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        ScaleAudioDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )

    assert ScaleAudioDialog.get_scale_value() is None


def test_get_scale_value_returns_value_when_accepted(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        ScaleAudioDialog, "exec", lambda self: QDialog.DialogCode.Accepted
    )

    assert ScaleAudioDialog.get_scale_value() == DEFAULT_SCALE_DBFS


def test_shows_current_peak_levels(qtbot: QtBot):
    from PyQt6.QtWidgets import QLabel

    dialog = ScaleAudioDialog(peaks_dbfs=[-4.1234, -6.0])
    qtbot.addWidget(dialog)

    texts = [label.text() for label in dialog.findChildren(QLabel)]
    assert any("-4.12 / -6.00 dBFS" in t for t in texts)
