import pytest
from PyQt6.QtWidgets import QDialog, QDialogButtonBox
from pytestqt.qtbot import QtBot

from ui.spectrogram.component.formant_settings_dialog import FormantSettingsDialog
from ui.spectrogram.state.formant_settings import FormantSettingsState


def test_fields_are_initialized_from_defaults(qtbot: QtBot):
    dialog = FormantSettingsDialog(FormantSettingsState())
    qtbot.addWidget(dialog)

    assert dialog.preemphasis_spin.value() == pytest.approx(0.94)
    assert dialog.f0_min_spin.value() == 70
    assert dialog.f0_max_spin.value() == 350
    assert dialog.speaker_combo.currentData() == 1


def test_ok_is_disabled_unless_f0_max_exceeds_f0_min(qtbot: QtBot):
    dialog = FormantSettingsDialog(FormantSettingsState())
    qtbot.addWidget(dialog)
    ok_button = dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)

    dialog.f0_max_spin.setValue(70)
    assert ok_button.isEnabled() is False

    dialog.f0_max_spin.setValue(71)
    assert ok_button.isEnabled() is True


def test_open_formant_settings_returns_updated_settings_when_accepted(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    def fake_exec(self: FormantSettingsDialog) -> QDialog.DialogCode:
        self.preemphasis_spin.setValue(0.5)
        self.f0_min_spin.setValue(60)
        self.f0_max_spin.setValue(500)
        self.speaker_combo.setCurrentIndex(self.speaker_combo.findData(2))
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(FormantSettingsDialog, "exec", fake_exec)

    result = FormantSettingsDialog.open_formant_settings(FormantSettingsState())

    assert result == FormantSettingsState(
        preemphasis=0.5, f0_min=60, f0_max=500, speaker=2
    )


def test_open_formant_settings_returns_none_when_rejected(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        FormantSettingsDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )

    assert FormantSettingsDialog.open_formant_settings(FormantSettingsState()) is None
