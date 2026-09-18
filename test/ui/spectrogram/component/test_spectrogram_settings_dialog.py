import pytest
from PyQt6.QtWidgets import QDialog
from pytestqt.qtbot import QtBot

from ui.spectrogram.component.spectrogram_settings_dialog import (
    SAMPLE_RATE_OPTIONS,
    SpectrogramSettingsDialog,
)
from ui.spectrogram.state.spectrogram_settings import SpectrogramSettingsState


def test_dropdown_is_populated_with_sorted_sample_rate_options(qtbot: QtBot):
    dialog = SpectrogramSettingsDialog(SpectrogramSettingsState())
    qtbot.addWidget(dialog)

    items = [dialog.fs_dropdown.itemData(i) for i in range(dialog.fs_dropdown.count())]
    assert items == sorted(SAMPLE_RATE_OPTIONS)


def test_fields_are_initialized_from_settings(qtbot: QtBot):
    settings = SpectrogramSettingsState(fs=32000, window_size=0.02, step_size=0.002)
    dialog = SpectrogramSettingsDialog(settings)
    qtbot.addWidget(dialog)

    assert dialog.fs_dropdown.currentData() == 32000
    assert dialog.window_spin.value() == 20
    assert dialog.step_spin.value() == 2


def test_open_spectrogram_settings_returns_updated_settings_when_accepted(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    def fake_exec(self: SpectrogramSettingsDialog) -> QDialog.DialogCode:
        self.fs_dropdown.setCurrentIndex(self.fs_dropdown.findData(44100))
        self.window_spin.setValue(15)
        self.step_spin.setValue(3)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(SpectrogramSettingsDialog, "exec", fake_exec)
    original = SpectrogramSettingsState(fs=16000, window_size=0.008, step_size=0.001)

    result = SpectrogramSettingsDialog.open_spectrogram_settings(original)

    assert result.fs == 44100
    assert result.window_size == pytest.approx(0.015)
    assert result.step_size == pytest.approx(0.003)


def test_open_spectrogram_settings_returns_none_when_rejected(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        SpectrogramSettingsDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )

    result = SpectrogramSettingsDialog.open_spectrogram_settings(
        SpectrogramSettingsState()
    )

    assert result is None
