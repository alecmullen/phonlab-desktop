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


def shown(dialog: SpectrogramSettingsDialog) -> set[str]:
    """The names of the type-specific settings the dialog offers"""
    dialog.show()
    widgets = {
        "top_frequency": dialog.top_frequency_dropdown,
        "nw": dialog.nw_spin,
        "bandwidth": dialog.bandwidth_label,
        "lift": dialog.lift_spin,
        "slow_warning": dialog.slow_warning,
    }
    return {name for name, widget in widgets.items() if widget.isVisible()}


def choose(dialog: SpectrogramSettingsDialog, type: SpectrogramTypeState):
    dialog.type_dropdown.setCurrentIndex(dialog.type_dropdown.findData(type))


def test_choosing_mel_fixes_the_window_and_removes_the_top_frequency(qtbot: QtBot):
    dialog = SpectrogramSettingsDialog(SpectrogramSettingsState())
    qtbot.addWidget(dialog)
    assert dialog.window_spin.isEnabled()
    assert "top_frequency" in shown(dialog)

    choose(dialog, SpectrogramTypeState.MEL)

    assert dialog.window_spin.value() == 64
    assert not dialog.window_spin.isEnabled()
    assert "top_frequency" not in shown(dialog)

    choose(dialog, SpectrogramTypeState.FFT)

    assert dialog.window_spin.isEnabled()
    assert "top_frequency" in shown(dialog)


def test_mel_always_returns_the_sampling_rate_its_filters_need(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    def fake_exec(self: SpectrogramSettingsDialog) -> QDialog.DialogCode:
        choose(self, SpectrogramTypeState.MEL)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(SpectrogramSettingsDialog, "exec", fake_exec)

    for fs in (8000, 16000, 32000):
        result = SpectrogramSettingsDialog.open_spectrogram_settings(
            SpectrogramSettingsState(fs=fs)
        )
        assert result.fs == 16000


def test_a_dialog_opened_on_mel_starts_with_the_limits_in_place(qtbot: QtBot):
    dialog = SpectrogramSettingsDialog(
        SpectrogramSettingsState().with_type(SpectrogramTypeState.MEL)
    )
    qtbot.addWidget(dialog)

    assert not dialog.window_spin.isEnabled()
    assert dialog.window_spin.value() == 64
    assert "top_frequency" not in shown(dialog)


@pytest.mark.parametrize(
    "type, offered",
    [
        (SpectrogramTypeState.FFT, {"top_frequency"}),
        (SpectrogramTypeState.MULTITAPER, {"top_frequency", "nw", "bandwidth"}),
        (SpectrogramTypeState.CEPSTRAL, {"top_frequency", "lift"}),
        (SpectrogramTypeState.LPC, {"top_frequency", "slow_warning"}),
        (SpectrogramTypeState.MEL, set()),
    ],
)
def test_only_the_chosen_types_settings_are_shown(
    qtbot: QtBot, type: SpectrogramTypeState, offered: set[str]
):
    dialog = SpectrogramSettingsDialog(SpectrogramSettingsState().with_type(type))
    qtbot.addWidget(dialog)

    assert shown(dialog) == offered


def test_lpc_warns_that_it_is_slower(qtbot: QtBot):
    dialog = SpectrogramSettingsDialog(SpectrogramSettingsState())
    qtbot.addWidget(dialog)

    assert "slower" in dialog.slow_warning.text()


def test_multitaper_reports_its_effective_filter_bandwidth(qtbot: QtBot):
    dialog = SpectrogramSettingsDialog(
        SpectrogramSettingsState().with_type(SpectrogramTypeState.MULTITAPER)
    )
    qtbot.addWidget(dialog)
    assert dialog.nw_spin.value() == 3.0
    assert dialog.window_spin.value() == 20
    assert (
        dialog.bandwidth_label.text() == "Effective filter bandwidth: 300 Hz"
    )  # 2 * 3 / 0.02 s

    dialog.nw_spin.setValue(4.0)

    assert dialog.bandwidth_label.text() == "Effective filter bandwidth: 400 Hz"

    dialog.window_spin.setValue(40)

    assert dialog.bandwidth_label.text() == "Effective filter bandwidth: 200 Hz"


def test_the_settings_keep_nw_and_lift_across_types(qtbot: QtBot):
    settings = SpectrogramSettingsState(multitaper_nw=5.0, cepstral_lift=0.004)
    dialog = SpectrogramSettingsDialog(settings)
    qtbot.addWidget(dialog)

    assert dialog.nw_spin.value() == 5.0
    assert dialog.lift_spin.value() == pytest.approx(4.0)
    assert settings.with_type(SpectrogramTypeState.LPC).multitaper_nw == 5.0
    assert settings.with_type(SpectrogramTypeState.LPC).cepstral_lift == 0.004


def test_open_spectrogram_settings_returns_nw_and_lift(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
):
    def fake_exec(self: SpectrogramSettingsDialog) -> QDialog.DialogCode:
        self.nw_spin.setValue(4.5)
        self.lift_spin.setValue(5.5)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(SpectrogramSettingsDialog, "exec", fake_exec)

    result = SpectrogramSettingsDialog.open_spectrogram_settings(
        SpectrogramSettingsState()
    )

    assert result.multitaper_nw == 4.5
    assert result.cepstral_lift == 0.0055


def test_a_link_points_to_the_chosen_types_documentation(qtbot: QtBot):
    dialog = SpectrogramSettingsDialog(SpectrogramSettingsState())
    qtbot.addWidget(dialog)
    assert dialog.docs_link.openExternalLinks()
    base = "https://phonlab.readthedocs.io/en/latest/"

    pages = {}
    for type in SpectrogramTypeState:
        choose(dialog, type)
        pages[type] = dialog.docs_link.text()

    assert f'href="{base}acoustphon.html#phonlab.compute_sgram"' in pages["fft"]
    assert f'href="{base}acoustphon.html#phonlab.RLPC_formants"' in pages["lpc"]  # the
    # LPC coefficients come from RLPC_formants
    assert f'href="{base}audphon.html#phonlab.compute_mel_sgram"' in pages["mel"]
    assert len(set(pages.values())) == len(SpectrogramTypeState)  # one each
