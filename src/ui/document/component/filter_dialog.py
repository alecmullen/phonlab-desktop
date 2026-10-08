from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QSpinBox,
)

from core.transform_audio.entity.filter_spec import FilterType
from core.transform_audio.filter_audio import FilterSpec
from res.constants import DEFAULT_FILTER_ORDER


class FilterAudioDialog(QDialog):
    """Collects Butterworth filter parameters for the given sample rate."""

    def __init__(self, fs: int):
        super().__init__()
        self.setWindowTitle(self.tr("Filter Audio"))
        nyquist = fs / 2

        layout = QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.type_combo = QComboBox()
        self.type_combo.addItem(self.tr("Bandpass"), FilterType.BANDPASS)
        self.type_combo.addItem(self.tr("Lowpass"), FilterType.LOWPASS)
        self.type_combo.addItem(self.tr("Highpass"), FilterType.HIGHPASS)
        layout.addRow(self.tr("Filter type:"), self.type_combo)

        self.low_label = QLabel()
        self.low_spin = self._hz_spin(nyquist, min(300.0, nyquist / 2))
        layout.addRow(self.low_label, self.low_spin)

        self.high_label = QLabel()
        self.high_spin = self._hz_spin(nyquist, min(3400.0, nyquist * 0.75))
        layout.addRow(self.high_label, self.high_spin)

        self.order_spin = QSpinBox()
        self.order_spin.setRange(1, 20)
        self.order_spin.setValue(DEFAULT_FILTER_ORDER)
        layout.addRow(self.tr("Order:"), self.order_spin)

        note = QLabel(
            self.tr(
                "Applies to the whole signal (active channels) and cannot be "
                "undone. Use Revert to Original to get the file's audio back."
            )
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: gray;")
        layout.addRow(note)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addRow(self.button_box)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        self.low_spin.valueChanged.connect(self._update_ok_enabled)
        self.high_spin.valueChanged.connect(self._update_ok_enabled)
        self._on_type_changed()

    @staticmethod
    def _hz_spin(nyquist: float, value: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(1)
        spin.setRange(1.0, max(1.0, nyquist - 1.0))
        spin.setSingleStep(100.0)
        spin.setSuffix(" Hz")
        spin.setValue(value)
        return spin

    def filter_type(self) -> FilterType:
        return FilterType(self.type_combo.currentData())

    def _on_type_changed(self):
        kind = self.filter_type()
        bandpass = kind == FilterType.BANDPASS
        self.low_label.setVisible(kind != FilterType.LOWPASS)
        self.low_spin.setVisible(kind != FilterType.LOWPASS)
        self.high_label.setVisible(kind != FilterType.HIGHPASS)
        self.high_spin.setVisible(kind != FilterType.HIGHPASS)
        self.low_label.setText(
            self.tr("Low edge:") if bandpass else self.tr("Cutoff frequency:")
        )
        self.high_label.setText(
            self.tr("High edge:") if bandpass else self.tr("Cutoff frequency:")
        )
        self._update_ok_enabled()

    def _update_ok_enabled(self):
        valid = (
            self.filter_type() != FilterType.BANDPASS
            or self.low_spin.value() < self.high_spin.value()
        )
        ok = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok is not None:
            ok.setEnabled(valid)

    def get_spec(self) -> FilterSpec:
        kind = self.filter_type()
        return FilterSpec(
            type=kind,
            low=None if kind == FilterType.LOWPASS else self.low_spin.value(),
            high=None if kind == FilterType.HIGHPASS else self.high_spin.value(),
            order=self.order_spin.value(),
        )

    @staticmethod
    def get_filter_spec(fs: int) -> FilterSpec | None:
        dialog = FilterAudioDialog(fs)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_spec()
        return None
