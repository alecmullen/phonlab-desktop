from dataclasses import replace

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
)

from ui.spectrogram.state.formant_settings import FormantSettingsState


class FormantSettingsDialog(QDialog):
    def __init__(self, settings: FormantSettingsState):
        super().__init__()

        self.setWindowTitle(self.tr("Track Formants"))

        layout = QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.preemphasis_spin = QDoubleSpinBox()
        self.preemphasis_spin.setRange(0.0, 1.0)
        self.preemphasis_spin.setSingleStep(0.01)
        self.preemphasis_spin.setDecimals(2)
        self.preemphasis_spin.setValue(settings.preemphasis)
        layout.addRow(self.tr("Preemphasis:"), self.preemphasis_spin)

        self.speaker_combo = QComboBox()
        self.speaker_combo.addItem(self.tr("Long vocal tract (male)"), 0)
        self.speaker_combo.addItem(self.tr("Medium (female)"), 1)
        self.speaker_combo.addItem(self.tr("Small (child)"), 2)
        self.speaker_combo.setCurrentIndex(
            self.speaker_combo.findData(settings.speaker)
        )
        layout.addRow(self.tr("Speaker:"), self.speaker_combo)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addRow(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    @staticmethod
    def open_formant_settings(
        settings: FormantSettingsState,
    ) -> FormantSettingsState | None:
        dialog = FormantSettingsDialog(settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return replace(
                settings,
                preemphasis=dialog.preemphasis_spin.value(),
                speaker=int(dialog.speaker_combo.currentData()),
            )
        return None
