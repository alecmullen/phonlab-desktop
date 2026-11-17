import pytest
from PyQt6.QtWidgets import QDialog
from pytestqt.qtbot import QtBot

from core.track_formants.entity.formant_options import FormantSpeakerType
from ui.spectrogram.component.formant_settings_dialog import FormantSettingsDialog
from ui.spectrogram.state.formant_settings import FormantSettingsState


def test_fields_are_initialized_from_defaults(qtbot: QtBot):
    dialog = FormantSettingsDialog(FormantSettingsState())
    qtbot.addWidget(dialog)

    assert dialog.preemphasis_spin.value() == pytest.approx(0.94)
    assert dialog.speaker_combo.currentData() == FormantSpeakerType.MEDIUM


def test_speaker_choices_map_to_ifc_speaker_values(qtbot: QtBot):
    dialog = FormantSettingsDialog(FormantSettingsState())
    qtbot.addWidget(dialog)

    combo = dialog.speaker_combo
    choices = [(combo.itemText(i), combo.itemData(i)) for i in range(combo.count())]
    assert choices == [
        ("Long vocal tract", FormantSpeakerType.LONG),
        ("Medium", FormantSpeakerType.MEDIUM),
        ("Short vocal tract", FormantSpeakerType.SHORT),
    ]


def test_open_formant_settings_returns_updated_settings_when_accepted(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    def fake_exec(self: FormantSettingsDialog) -> QDialog.DialogCode:
        self.preemphasis_spin.setValue(0.5)
        self.speaker_combo.setCurrentIndex(
            self.speaker_combo.findData(FormantSpeakerType.SHORT)
        )
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(FormantSettingsDialog, "exec", fake_exec)

    result = FormantSettingsDialog.open_formant_settings(FormantSettingsState())

    assert result == FormantSettingsState(
        preemphasis=0.5, speaker=FormantSpeakerType.SHORT
    )


def test_open_formant_settings_returns_none_when_rejected(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        FormantSettingsDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )

    assert FormantSettingsDialog.open_formant_settings(FormantSettingsState()) is None
