from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QSpinBox,
)

from ui.common.sample_rate_dropdown import SampleRateDropdown
from ui.spectrogram.state.spectrogram_settings import (
    SpectrogramSettingsState,
    SpectrogramTypeState,
)

# The top frequency is the Nyquist frequency, so the spectrogram's sampling
# rate is twice the chosen value.
TOP_FREQUENCY_OPTIONS = [4000, 5000, 8000, 12000, 16000]


class SpectrogramSettingsDialog(QDialog):
    def __init__(self, settings: SpectrogramSettingsState):
        super().__init__()

        self.setWindowTitle(self.tr("Spectrogram Settings"))

        layout = QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.type_dropdown = QComboBox()
        for type, label in self.type_labels().items():
            self.type_dropdown.addItem(label, type)
        self.type_dropdown.setCurrentIndex(self.type_dropdown.findData(settings.type))
        layout.addRow(self.tr("Type:"), self.type_dropdown)

        top_frequencies = sorted(TOP_FREQUENCY_OPTIONS)

        self.top_frequency_dropdown = SampleRateDropdown(
            top_frequencies, settings.fs // 2
        )
        layout.addRow(self.tr("Top frequency:"), self.top_frequency_dropdown)

        self.window_spin = QSpinBox()
        self.window_spin.setRange(5, 60)
        self.window_spin.setSingleStep(1)
        self.window_spin.setValue(round(settings.window_size * 1000))
        self.window_spin.setSuffix(self.tr(" ms"))
        layout.addRow(self.tr("Window size:"), self.window_spin)

        self.step_spin = QSpinBox()
        self.step_spin.setRange(1, 4)
        self.step_spin.setSingleStep(1)
        self.step_spin.setValue(round(settings.step_size * 1000))
        self.step_spin.setSuffix(self.tr(" ms"))
        layout.addRow(self.tr("Step size:"), self.step_spin)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addRow(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        self.type_dropdown.currentIndexChanged.connect(self.on_type_changed)

    def type_labels(self) -> dict[SpectrogramTypeState, str]:
        return {
            SpectrogramTypeState.FFT: self.tr("FFT"),
            SpectrogramTypeState.MULTITAPER: self.tr("Multitaper"),
            SpectrogramTypeState.CEPSTRAL: self.tr("Cepstral (smoothed)"),
            SpectrogramTypeState.LPC: self.tr("LPC"),
        }

    def on_type_changed(self):
        """Update to default window and step for the sgram type"""
        defaults = SpectrogramSettingsState().with_type(
            self.type_dropdown.currentData()
        )
        self.window_spin.setValue(round(defaults.window_size * 1000))
        self.step_spin.setValue(round(defaults.step_size * 1000))

    @staticmethod
    def open_spectrogram_settings(
        settings: SpectrogramSettingsState,
    ) -> SpectrogramSettingsState | None:
        dialog = SpectrogramSettingsDialog(settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return SpectrogramSettingsState(
                fs=2 * int(dialog.top_frequency_dropdown.currentData()),
                window_size=dialog.window_spin.value() / 1000,
                step_size=dialog.step_spin.value() / 1000,
                type=dialog.type_dropdown.currentData(),
            )
        else:
            return None
