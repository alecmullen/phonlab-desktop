from dataclasses import replace

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QSpinBox

from ui.common.sample_rate_dropdown import SampleRateDropdown
from ui.spectrogram.state.spectrogram_settings import SpectrogramSettingsState

# The top frequency is the Nyquist frequency, so the spectrogram's sampling
# rate is twice the chosen value.
TOP_FREQUENCY_OPTIONS = [4000, 5000, 8000, 12000, 16000]


class SpectrogramSettingsDialog(QDialog):
    def __init__(self, settings: SpectrogramSettingsState):
        super().__init__()

        self.setWindowTitle(self.tr("Spectrogram Settings"))

        layout = QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        top_frequencies = sorted(TOP_FREQUENCY_OPTIONS)

        self.top_frequency_dropdown = SampleRateDropdown(
            top_frequencies, settings.fs // 2
        )
        layout.addRow(self.tr("Top frequency:"), self.top_frequency_dropdown)

        self.window_spin = QSpinBox()
        self.window_spin.setRange(5, 60)
        self.window_spin.setSingleStep(1)
        self.window_spin.setValue(int(settings.window_size * 1000))
        self.window_spin.setSuffix(self.tr(" ms"))
        layout.addRow(self.tr("Window size:"), self.window_spin)

        self.step_spin = QSpinBox()
        self.step_spin.setRange(1, 4)
        self.step_spin.setSingleStep(1)
        self.step_spin.setValue(int(settings.step_size * 1000))
        self.step_spin.setSuffix(self.tr(" ms"))
        layout.addRow(self.tr("Step size:"), self.step_spin)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addRow(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    @staticmethod
    def open_spectrogram_settings(
        settings: SpectrogramSettingsState,
    ) -> SpectrogramSettingsState | None:
        dialog = SpectrogramSettingsDialog(settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return replace(
                settings,
                fs=2 * int(dialog.top_frequency_dropdown.currentData()),
                window_size=dialog.window_spin.value() / 1000,
                step_size=dialog.step_spin.value() / 1000,
            )
        else:
            return None
