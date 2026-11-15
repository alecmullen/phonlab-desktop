import pytest
from PyQt6.QtWidgets import QDialog
from pytestqt.qtbot import QtBot

from ui.spectrogram.component.formant_settings_dialog import FormantSettingsDialog
from ui.spectrogram.state.formant_settings import (
    FormantMethodState,
    FormantSettingsState,
)


def test_fields_are_initialized_from_defaults(qtbot: QtBot):
    dialog = FormantSettingsDialog(FormantSettingsState())
    qtbot.addWidget(dialog)

    assert dialog.preemphasis_spin.value() == pytest.approx(0.94)
    assert dialog.speaker_combo.currentData() == 1
    # IFC is the default method
    assert dialog.method() == FormantMethodState.IFC
    methods = [
        dialog.method_combo.itemData(i) for i in range(dialog.method_combo.count())
    ]
    assert methods == ["ifc", "lpc", "rlpc", "tvlp", "dppt"]


def test_speaker_choices_map_to_ifc_speaker_values(qtbot: QtBot):
    dialog = FormantSettingsDialog(FormantSettingsState())
    qtbot.addWidget(dialog)

    combo = dialog.speaker_combo
    choices = [(combo.itemText(i), combo.itemData(i)) for i in range(combo.count())]
    assert choices == [
        ("Long vocal tract", 0),
        ("Medium", 1),
        ("Short vocal tract", 2),
    ]


def test_open_formant_settings_returns_updated_settings_when_accepted(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    def fake_exec(self: FormantSettingsDialog) -> QDialog.DialogCode:
        self.preemphasis_spin.setValue(0.5)
        self.speaker_combo.setCurrentIndex(self.speaker_combo.findData(2))
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(FormantSettingsDialog, "exec", fake_exec)

    result = FormantSettingsDialog.open_formant_settings(FormantSettingsState())

    assert result == FormantSettingsState(preemphasis=0.5, speaker=2)


def test_open_formant_settings_returns_none_when_rejected(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        FormantSettingsDialog, "exec", lambda self: QDialog.DialogCode.Rejected
    )

    assert FormantSettingsDialog.open_formant_settings(FormantSettingsState()) is None


def shown(dialog: FormantSettingsDialog) -> dict[str, bool]:
    """Whether each method-specific setting is offered, by its row's widget"""
    dialog.show()
    return {
        "speaker": dialog.speaker_combo.isVisible(),
        "order": dialog.order_spin.isVisible(),
        "top_frequency": dialog.top_frequency_spin.isVisible(),
        "median_f0": dialog.median_f0_spin.isVisible(),
        "delta_f": dialog.delta_f_spin.isVisible(),
        "slow_warning": dialog.slow_warning.isVisible(),
    }


@pytest.mark.parametrize(
    "method, offered",
    [
        (FormantMethodState.IFC, {"speaker"}),
        (FormantMethodState.LPC, {"order"}),
        (FormantMethodState.RLPC, {"order", "top_frequency"}),
        (FormantMethodState.TVLP, {"order", "top_frequency", "median_f0", "slow_warning"}),
        (FormantMethodState.DPPT, {"delta_f"}),
    ],
)  # fmt: skip
def test_only_the_chosen_methods_settings_are_shown(
    qtbot: QtBot, method: FormantMethodState, offered: set[str]
):
    dialog = FormantSettingsDialog(FormantSettingsState().with_method(method))
    qtbot.addWidget(dialog)

    assert {name for name, visible in shown(dialog).items() if visible} == offered


def test_changing_the_method_changes_the_settings_shown_and_preemphasis(qtbot: QtBot):
    dialog = FormantSettingsDialog(FormantSettingsState())
    qtbot.addWidget(dialog)
    assert shown(dialog)["speaker"]

    dialog.method_combo.setCurrentIndex(dialog.method_combo.findData("dppt"))

    assert shown(dialog)["delta_f"]
    assert not shown(dialog)["speaker"]
    assert dialog.preemphasis_spin.value() == 0.0  # DPPT's usual preemphasis

    dialog.method_combo.setCurrentIndex(dialog.method_combo.findData("tvlp"))

    assert dialog.preemphasis_spin.value() == pytest.approx(0.95)
    assert shown(dialog)["slow_warning"]


def test_tvlp_warns_that_it_is_slower(qtbot: QtBot):
    dialog = FormantSettingsDialog(FormantSettingsState())
    qtbot.addWidget(dialog)

    assert "slower" in dialog.slow_warning.text()


def test_order_spin_is_automatic_at_its_lowest_value(qtbot: QtBot):
    dialog = FormantSettingsDialog(
        FormantSettingsState().with_method(FormantMethodState.LPC)
    )
    qtbot.addWidget(dialog)

    assert dialog.order_spin.text() == "Automatic"
    assert dialog.chosen_order() == -1

    dialog.order_spin.setValue(12)

    assert dialog.chosen_order() == 12


def test_open_formant_settings_returns_the_chosen_method_and_its_settings(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    def fake_exec(self: FormantSettingsDialog) -> QDialog.DialogCode:
        self.method_combo.setCurrentIndex(self.method_combo.findData("tvlp"))
        self.order_spin.setValue(14)
        self.top_frequency_spin.setValue(8000)
        self.median_f0_spin.setValue(120)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(FormantSettingsDialog, "exec", fake_exec)

    result = FormantSettingsDialog.open_formant_settings(FormantSettingsState())

    assert result == FormantSettingsState(
        FormantMethodState.TVLP,
        preemphasis=0.95,
        order=14,
        top_frequency=8000,
        median_f0=120,
    )
