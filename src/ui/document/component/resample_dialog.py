import bisect

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
)

SAMPLE_RATE_OPTIONS = [4000, 8000, 16000, 32000, 44100, 48000, 96000]


class ResampleAudioDialog(QDialog):
    def __init__(self, current_fs: int):
        super().__init__()
        self.is_entering_custom = False

        sample_rates = sorted(SAMPLE_RATE_OPTIONS)

        self.setWindowTitle(self.tr("Resample Audio"))

        layout = QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.fs_dropdown = QComboBox()
        for fs in sample_rates:
            self.fs_dropdown.addItem(f"{fs} Hz", fs)
        self.fs_dropdown.setCurrentIndex(bisect.bisect_left(sample_rates, current_fs))
        layout.addRow(self.tr("Target sample rate:"), self.fs_dropdown)

        layout.addItem(
            QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        )

        self.custom_check_box = QCheckBox(self.tr("Enter custom sample rate"))
        layout.addRow(self.custom_check_box)

        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(1000, 384000)
        self.rate_spin.setSingleStep(1000)
        self.rate_spin.setValue(current_fs)
        self.rate_spin.setSuffix(self.tr(" Hz"))
        self.rate_spin.setVisible(False)

        self.optional_rate_line = QHBoxLayout()
        self.optional_rate_line.addSpacerItem(
            QSpacerItem(20, 10, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        )
        self.optional_rate_line.addWidget(self.rate_spin)
        layout.addRow(self.optional_rate_line)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addRow(button_box)

        self.custom_check_box.toggled.connect(self.set_is_entering_custom)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    pyqtSlot(bool)

    def set_is_entering_custom(self, value: bool):
        self.is_entering_custom = value
        self.rate_spin.setVisible(value)
        self.fs_dropdown.setDisabled(value)

    def get_sample_rate(self) -> int:
        if self.is_entering_custom:
            return self.rate_spin.value()
        else:
            return int(self.fs_dropdown.currentData())

    @staticmethod
    def get_target_fs(current_fs: int) -> int | None:
        resample_dialog = ResampleAudioDialog(current_fs)
        if resample_dialog.exec() == QDialog.DialogCode.Accepted:
            return resample_dialog.get_sample_rate()
        else:
            return None
