import pytest
from PyQt6.QtWidgets import QDialog, QDialogButtonBox
from pytestqt.qtbot import QtBot

from core.edit_audio.filter_audio import FilterType
from ui.document.component.filter_dialog import FilterAudioDialog


def select_type(dialog: FilterAudioDialog, kind: FilterType):
    dialog.type_combo.setCurrentIndex(dialog.type_combo.findData(kind))


def test_defaults_to_bandpass_with_both_edges(qtbot: QtBot):
    dialog = FilterAudioDialog(16000)
    qtbot.addWidget(dialog)
    dialog.show()

    spec = dialog.get_spec()

    assert spec.type == FilterType.BANDPASS
    assert spec.low is not None and spec.high is not None and spec.low < spec.high
    assert dialog.low_spin.isVisible() and dialog.high_spin.isVisible()


def test_lowpass_uses_only_high_and_highpass_only_low(qtbot: QtBot):
    dialog = FilterAudioDialog(16000)
    qtbot.addWidget(dialog)
    dialog.show()

    select_type(dialog, FilterType.LOWPASS)
    spec = dialog.get_spec()
    assert spec.low is None and spec.high is not None
    assert not dialog.low_spin.isVisible()

    select_type(dialog, FilterType.HIGHPASS)
    spec = dialog.get_spec()
    assert spec.high is None and spec.low is not None
    assert not dialog.high_spin.isVisible()


def test_ok_disabled_when_bandpass_edges_inverted(qtbot: QtBot):
    dialog = FilterAudioDialog(16000)
    qtbot.addWidget(dialog)
    ok = dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)

    dialog.low_spin.setValue(2000)
    dialog.high_spin.setValue(1000)
    assert not ok.isEnabled()

    select_type(dialog, FilterType.LOWPASS)
    assert ok.isEnabled()


def test_cutoffs_stay_below_nyquist(qtbot: QtBot):
    dialog = FilterAudioDialog(8000)
    qtbot.addWidget(dialog)

    assert dialog.high_spin.maximum() < 4000


def test_get_filter_spec_cancel_and_accept(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        FilterAudioDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )
    assert FilterAudioDialog.get_filter_spec(16000) is None

    monkeypatch.setattr(
        FilterAudioDialog, "exec", lambda self: QDialog.DialogCode.Accepted
    )
    assert FilterAudioDialog.get_filter_spec(16000) is not None
