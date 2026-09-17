import pytest
from PyQt6.QtWidgets import QDialog
from pytestqt.qtbot import QtBot

from ui.document.component.resample_dialog import (
    SAMPLE_RATE_OPTIONS,
    ResampleAudioDialog,
)


def test_dropdown_is_populated_with_sorted_sample_rate_options(qtbot: QtBot):
    dialog = ResampleAudioDialog(22050)
    qtbot.addWidget(dialog)

    items = [dialog.fs_dropdown.itemData(i) for i in range(dialog.fs_dropdown.count())]
    assert items == sorted(SAMPLE_RATE_OPTIONS)


def test_dropdown_selects_exact_match_for_current_fs(qtbot: QtBot):
    dialog = ResampleAudioDialog(4000)
    qtbot.addWidget(dialog)

    assert dialog.fs_dropdown.currentData() == 4000


def test_dropdown_selects_nearest_rate_above_current_fs(qtbot: QtBot):
    dialog = ResampleAudioDialog(22049)
    qtbot.addWidget(dialog)

    assert dialog.fs_dropdown.currentData() == 22050


def test_dropdown_selects_nearest_rate_below_current_fs(qtbot: QtBot):
    dialog = ResampleAudioDialog(22051)
    qtbot.addWidget(dialog)

    assert dialog.fs_dropdown.currentData() == 22050


def test_get_sample_rate_returns_dropdown_value_by_default(qtbot: QtBot):
    dialog = ResampleAudioDialog(16000)
    qtbot.addWidget(dialog)

    assert dialog.get_sample_rate() == 16000


def test_checking_custom_reveals_spin_box_and_disables_dropdown(qtbot: QtBot):
    dialog = ResampleAudioDialog(16000)
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.custom_check_box.setChecked(True)

    assert dialog.is_entering_custom is True
    assert dialog.rate_spin.isVisible() is True
    assert dialog.fs_dropdown.isEnabled() is False


def test_unchecking_custom_hides_spin_box_and_enables_dropdown(qtbot: QtBot):
    dialog = ResampleAudioDialog(16000)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.custom_check_box.setChecked(True)

    dialog.custom_check_box.setChecked(False)

    assert dialog.is_entering_custom is False
    assert dialog.rate_spin.isVisible() is False
    assert dialog.fs_dropdown.isEnabled() is True


def test_get_sample_rate_returns_spin_value_when_entering_custom(qtbot: QtBot):
    dialog = ResampleAudioDialog(16000)
    qtbot.addWidget(dialog)
    dialog.custom_check_box.setChecked(True)
    dialog.rate_spin.setValue(12345)

    assert dialog.get_sample_rate() == 12345


def test_get_target_fs_returns_selected_rate_when_accepted(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        ResampleAudioDialog, "exec", lambda self: QDialog.DialogCode.Accepted
    )

    result = ResampleAudioDialog.get_target_fs(22050)

    assert result == 22050


def test_get_target_fs_returns_none_when_rejected(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        ResampleAudioDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )

    result = ResampleAudioDialog.get_target_fs(22050)

    assert result is None
