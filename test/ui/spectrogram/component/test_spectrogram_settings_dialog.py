import pytest
from PyQt6.QtWidgets import QDialog
from pytestqt.qtbot import QtBot

from ui.spectrogram.component.spectrogram_settings_dialog import (
    TOP_FREQUENCY_OPTIONS,
    SpectrogramSettingsDialog,
)
from ui.spectrogram.state.spectrogram_settings import (
    SpectrogramSettingsState,
    SpectrogramTypeState,
)


def test_dropdown_is_populated_with_sorted_top_frequency_options(qtbot: QtBot):
    dialog = SpectrogramSettingsDialog(SpectrogramSettingsState())
    qtbot.addWidget(dialog)

    dropdown = dialog.top_frequency_dropdown
    items = [dropdown.itemData(i) for i in range(dropdown.count())]
    assert items == sorted(TOP_FREQUENCY_OPTIONS)
    assert items == [4000, 5000, 8000, 12000, 16000]


def test_fields_are_initialized_from_settings(qtbot: QtBot):
    settings = SpectrogramSettingsState(fs=32000, window_size=0.02, step_size=0.002)
    dialog = SpectrogramSettingsDialog(settings)
    qtbot.addWidget(dialog)

    assert dialog.top_frequency_dropdown.currentData() == 16000
    assert dialog.window_spin.value() == 20
    assert dialog.step_spin.value() == 2


def test_open_spectrogram_settings_returns_updated_settings_when_accepted(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    def fake_exec(self: SpectrogramSettingsDialog) -> QDialog.DialogCode:
        dropdown = self.top_frequency_dropdown
        dropdown.setCurrentIndex(dropdown.findData(12000))
        self.window_spin.setValue(15)
        self.step_spin.setValue(3)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(SpectrogramSettingsDialog, "exec", fake_exec)
    original = SpectrogramSettingsState(fs=16000, window_size=0.008, step_size=0.001)

    result = SpectrogramSettingsDialog.open_spectrogram_settings(original)

    assert result.fs == 24000  # twice the top frequency
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


def test_type_dropdown_offers_the_four_types_and_shows_the_current_one(qtbot: QtBot):
    settings = SpectrogramSettingsState().with_type(SpectrogramTypeState.LPC)
    dialog = SpectrogramSettingsDialog(settings)
    qtbot.addWidget(dialog)

    dropdown = dialog.type_dropdown
    assert [dropdown.itemData(i) for i in range(dropdown.count())] == list(
        SpectrogramTypeState
    )
    assert dropdown.currentData() == SpectrogramTypeState.LPC
    # Opening the dialog must not replace the user's own window and step
    assert dialog.window_spin.value() == 30
    assert dialog.step_spin.value() == 4


def test_choosing_a_type_fills_in_its_usual_window_and_step(qtbot: QtBot):
    dialog = SpectrogramSettingsDialog(SpectrogramSettingsState())
    qtbot.addWidget(dialog)

    dialog.type_dropdown.setCurrentIndex(
        dialog.type_dropdown.findData(SpectrogramTypeState.MULTITAPER)
    )

    assert dialog.window_spin.value() == 20
    assert dialog.step_spin.value() == 4

    dialog.type_dropdown.setCurrentIndex(
        dialog.type_dropdown.findData(SpectrogramTypeState.FFT)
    )

    assert dialog.window_spin.value() == 8
    assert dialog.step_spin.value() == 1


def test_the_step_can_be_lowered_after_choosing_a_slow_type(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    def fake_exec(self: SpectrogramSettingsDialog) -> QDialog.DialogCode:
        self.type_dropdown.setCurrentIndex(
            self.type_dropdown.findData(SpectrogramTypeState.LPC)
        )
        self.step_spin.setValue(1)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(SpectrogramSettingsDialog, "exec", fake_exec)

    result = SpectrogramSettingsDialog.open_spectrogram_settings(
        SpectrogramSettingsState()
    )

    assert result.type == SpectrogramTypeState.LPC
    assert result.window_size == pytest.approx(0.03)
    assert result.step_size == pytest.approx(0.001)


def test_the_returned_order_follows_the_new_window(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    def fake_exec(self: SpectrogramSettingsDialog) -> QDialog.DialogCode:
        self.window_spin.setValue(8)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(SpectrogramSettingsDialog, "exec", fake_exec)
    # A long window earlier made the order bigger than the default
    original = SpectrogramSettingsState(window_size=0.04)
    assert original.order == 10

    result = SpectrogramSettingsDialog.open_spectrogram_settings(original)

    assert result.order == 9  # the default again


def test_choosing_mel_fixes_the_window_and_rules_out_low_top_frequencies(
    qtbot: QtBot,
):
    dialog = SpectrogramSettingsDialog(
        SpectrogramSettingsState(fs=8000)  # a top frequency of 4000
    )
    qtbot.addWidget(dialog)
    dropdown = dialog.top_frequency_dropdown
    assert dropdown.currentData() == 4000
    assert dialog.window_spin.isEnabled()

    dialog.type_dropdown.setCurrentIndex(
        dialog.type_dropdown.findData(SpectrogramTypeState.MEL)
    )

    assert dialog.window_spin.value() == 64
    assert not dialog.window_spin.isEnabled()
    assert dropdown.currentData() == 8000
    enabled = [
        dropdown.itemData(i)
        for i in range(dropdown.count())
        if dropdown.model().item(i).isEnabled()
    ]
    assert enabled == [8000, 12000, 16000]

    dialog.type_dropdown.setCurrentIndex(
        dialog.type_dropdown.findData(SpectrogramTypeState.FFT)
    )

    assert dialog.window_spin.isEnabled()
    assert all(dropdown.model().item(i).isEnabled() for i in range(dropdown.count()))


def test_a_dialog_opened_on_mel_starts_with_the_limits_in_place(qtbot: QtBot):
    dialog = SpectrogramSettingsDialog(
        SpectrogramSettingsState().with_type(SpectrogramTypeState.MEL)
    )
    qtbot.addWidget(dialog)

    assert not dialog.window_spin.isEnabled()
    assert dialog.window_spin.value() == 64
    assert not dialog.top_frequency_dropdown.model().item(0).isEnabled()
