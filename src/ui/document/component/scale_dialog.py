from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
)

DEFAULT_SCALE_DBFS = -1.0


class ScaleAudioDialog(QDialog):
    """Asks for the peak level, in dBFS, to scale the audio to."""

    def __init__(
        self, applies_to_selection: bool = False, peaks_dbfs: list[float] | None = None
    ):
        super().__init__()
        self.setWindowTitle(self.tr("Scale Audio"))

        layout = QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        target = (
            self.tr("the selection") if applies_to_selection else self.tr("the audio")
        )
        layout.addRow(
            QLabel(self.tr("Scale the peak amplitude of {} to:").format(target))
        )

        if peaks_dbfs:
            levels = " / ".join(f"{p:.2f}" for p in peaks_dbfs)
            layout.addRow(QLabel(self.tr("Current peak level: {} dBFS").format(levels)))

        self.scale_edit = QLineEdit(str(DEFAULT_SCALE_DBFS))
        validator = QDoubleValidator(-200.0, 200.0, 4, self.scale_edit)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.scale_edit.setValidator(validator)
        layout.addRow(self.tr("Peak level (dBFS):"), self.scale_edit)

        hint = QLabel(self.tr("0 is full scale; -3 is about 0.71 of full scale."))
        hint.setStyleSheet("color: gray;")
        layout.addRow(hint)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addRow(self.button_box)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.scale_edit.textChanged.connect(self._update_ok_enabled)
        self._update_ok_enabled()

    def _update_ok_enabled(self):
        ok = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok is not None:
            ok.setEnabled(self.scale_edit.hasAcceptableInput())

    def get_scale(self) -> float:
        return float(self.scale_edit.text())

    @staticmethod
    def get_scale_value(
        applies_to_selection: bool = False, peaks_dbfs: list[float] | None = None
    ) -> float | None:
        dialog = ScaleAudioDialog(applies_to_selection, peaks_dbfs)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_scale()
        return None
