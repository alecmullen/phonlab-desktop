import bisect
from dataclasses import replace

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QSpinBox

from ui.spectrogram.state.spectrogram_settings import SpectrogramSettingsState

SAMPLE_RATE_OPTIONS = [4000, 8000, 16000, 32000, 44100, 48000, 96000]


class SpectrogramSettingsDialog(QDialog):
    def __init__(self, settings: SpectrogramSettingsState):
        super().__init__()

        self.setWindowTitle(self.tr("Spectrogram Settings"))

        layout = QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        sample_rates = sorted(SAMPLE_RATE_OPTIONS)

        self.fs_dropdown = QComboBox()
        for fs in sample_rates:
            self.fs_dropdown.addItem(f"{fs} Hz", fs)
        self.fs_dropdown.setCurrentIndex(bisect.bisect_left(sample_rates, settings.fs))
        layout.addRow(self.tr("Sample rate:"), self.fs_dropdown)

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
                fs=int(dialog.fs_dropdown.currentData()),
                window_size=dialog.window_spin.value() / 1000,
                step_size=dialog.step_spin.value() / 1000,
            )
        else:
            return None
