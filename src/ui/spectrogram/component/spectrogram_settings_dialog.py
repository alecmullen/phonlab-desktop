from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QWidget,
)

from res.constants import MEL_MIN_TOP_FREQUENCY, PHONLAB_DOCS_URL, SPECTROGRAM_DOCS
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

        self.form = layout = QFormLayout(self)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.type_dropdown = QComboBox()
        for type, label in self.type_labels().items():
            self.type_dropdown.addItem(label, type)
        self.type_dropdown.setCurrentIndex(self.type_dropdown.findData(settings.type))
        layout.addRow(self.tr("Type:"), self.type_dropdown)

        self.docs_link = QLabel()
        self.docs_link.setTextFormat(Qt.TextFormat.RichText)
        self.docs_link.setOpenExternalLinks(True)
        layout.addRow(self.docs_link)

        top_frequencies = sorted(TOP_FREQUENCY_OPTIONS)

        self.top_frequency_dropdown = SampleRateDropdown(
            top_frequencies, settings.fs // 2
        )
        layout.addRow(self.tr("Top frequency:"), self.top_frequency_dropdown)

        self.window_spin = QSpinBox()
        self.window_spin.setRange(5, 70)  # the mel type's fixed window is 64
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

        self.nw_spin = QDoubleSpinBox()
        self.nw_spin.setRange(1.0, 10.0)
        self.nw_spin.setSingleStep(0.5)
        self.nw_spin.setDecimals(1)
        self.nw_spin.setValue(settings.multitaper_nw)
        layout.addRow(self.tr("Time-bandwidth product (NW):"), self.nw_spin)

        self.bandwidth_label = QLabel()
        layout.addRow(self.bandwidth_label)

        self.lift_spin = QDoubleSpinBox()
        self.lift_spin.setRange(0.5, 20.0)
        self.lift_spin.setSingleStep(0.5)
        self.lift_spin.setDecimals(1)
        self.lift_spin.setValue(settings.cepstral_lift * 1000)
        self.lift_spin.setSuffix(self.tr(" ms"))
        layout.addRow(self.tr("Lift:"), self.lift_spin)

        self.slow_warning = QLabel(
            self.tr("Linear predictive coding is slower than the other types.")
        )
        self.slow_warning.setWordWrap(True)
        layout.addRow(self.slow_warning)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addRow(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        self.limit_to_type()
        self.type_dropdown.currentIndexChanged.connect(self.on_type_changed)
        self.nw_spin.valueChanged.connect(self.update_bandwidth)
        self.window_spin.valueChanged.connect(self.update_bandwidth)

    def type_labels(self) -> dict[SpectrogramTypeState, str]:
        return {
            SpectrogramTypeState.FFT: self.tr("Fourier Transform"),
            SpectrogramTypeState.MULTITAPER: self.tr("Multitaper"),
            SpectrogramTypeState.CEPSTRAL: self.tr("Cepstral (smoothed)"),
            SpectrogramTypeState.LPC: self.tr("Linear Predictive Coding (LPC)"),
            SpectrogramTypeState.MEL: self.tr("Mel"),
        }

    def on_type_changed(self):
        """Each type has its own usual window and step (the slower types take a
        longer step). They are only a starting point, so the user can still
        change them"""
        defaults = SpectrogramSettingsState().with_type(
            self.type_dropdown.currentData()
        )
        self.window_spin.setValue(round(defaults.window_size * 1000))
        self.step_spin.setValue(round(defaults.step_size * 1000))
        self.limit_to_type()

    def limit_to_type(self):
        """Show only the settings the chosen type uses. The mel type has a
        window of its own (fixed), and filters that reach a fixed 7600 Hz, so it
        has no top frequency to choose."""
        type = self.type_dropdown.currentData()
        self.window_spin.setEnabled(type != SpectrogramTypeState.MEL)

        shown: dict[QWidget, bool] = {
            self.top_frequency_dropdown: type != SpectrogramTypeState.MEL,
            self.nw_spin: type == SpectrogramTypeState.MULTITAPER,
            self.bandwidth_label: type == SpectrogramTypeState.MULTITAPER,
            self.lift_spin: type == SpectrogramTypeState.CEPSTRAL,
            self.slow_warning: type == SpectrogramTypeState.LPC,
        }
        for widget, visible in shown.items():
            self.form.setRowVisible(widget, visible)

        page = SPECTROGRAM_DOCS[type.value]
        name = page.split("phonlab.")[-1]
        self.docs_link.setText(
            self.tr("Documentation: {}").format(
                f'<a href="{PHONLAB_DOCS_URL}{page}">{name}()</a>'
            )
        )
        self.update_bandwidth()
        self.adjustSize()

    def update_bandwidth(self):
        """The multitaper's effective filter bandwidth is NW / window length"""
        bandwidth = self.nw_spin.value() / (self.window_spin.value() / 1000)
        self.bandwidth_label.setText(
            self.tr("Effective filter bandwidth: {} Hz").format(round(bandwidth))
        )

    @staticmethod
    def open_spectrogram_settings(
        settings: SpectrogramSettingsState,
    ) -> SpectrogramSettingsState | None:
        dialog = SpectrogramSettingsDialog(settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # A new state, not a copy: the FFT order is worked out from the window
            type = dialog.type_dropdown.currentData()
            top_frequency = (
                MEL_MIN_TOP_FREQUENCY
                if type == SpectrogramTypeState.MEL
                else int(dialog.top_frequency_dropdown.currentData())
            )
            return SpectrogramSettingsState(
                fs=2 * top_frequency,
                window_size=dialog.window_spin.value() / 1000,
                step_size=dialog.step_spin.value() / 1000,
                type=type,
                multitaper_nw=dialog.nw_spin.value(),
                cepstral_lift=round(dialog.lift_spin.value() / 1000, 6),
            )
        else:
            return None
