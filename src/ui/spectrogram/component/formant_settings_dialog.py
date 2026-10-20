from dataclasses import replace

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QSpinBox,
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

        self.f0_min_spin = QSpinBox()
        self.f0_min_spin.setRange(20, 1000)
        self.f0_min_spin.setSuffix(self.tr(" Hz"))
        self.f0_min_spin.setValue(settings.f0_min)
        layout.addRow(self.tr("F0 minimum:"), self.f0_min_spin)

        self.f0_max_spin = QSpinBox()
        self.f0_max_spin.setRange(20, 1000)
        self.f0_max_spin.setSuffix(self.tr(" Hz"))
        self.f0_max_spin.setValue(settings.f0_max)
        layout.addRow(self.tr("F0 maximum:"), self.f0_max_spin)

        self.speaker_combo = QComboBox()
        self.speaker_combo.addItem(self.tr("Long vocal tract (male)"), 0)
        self.speaker_combo.addItem(self.tr("Medium (female)"), 1)
        self.speaker_combo.addItem(self.tr("Small (child)"), 2)
        self.speaker_combo.setCurrentIndex(
            self.speaker_combo.findData(settings.speaker)
        )
        layout.addRow(self.tr("Speaker:"), self.speaker_combo)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addRow(self.button_box)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.f0_min_spin.valueChanged.connect(self.validate)
        self.f0_max_spin.valueChanged.connect(self.validate)
        self.validate()

    def validate(self):
        """F0 maximum must exceed F0 minimum."""
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setEnabled(self.f0_max_spin.value() > self.f0_min_spin.value())

    @staticmethod
    def open_formant_settings(
        settings: FormantSettingsState,
    ) -> FormantSettingsState | None:
        dialog = FormantSettingsDialog(settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return replace(
                settings,
                preemphasis=dialog.preemphasis_spin.value(),
                f0_min=dialog.f0_min_spin.value(),
                f0_max=dialog.f0_max_spin.value(),
                speaker=int(dialog.speaker_combo.currentData()),
            )
        return None
