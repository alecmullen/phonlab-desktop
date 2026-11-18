from dataclasses import replace

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QWidget,
)

from core.track_formants.entity.formant_options import FormantSpeakerType
from res.constants import (
    FORMANT_AUTO_ORDER,
    FORMANT_DOCS,
    FORMANT_MAX_ORDER,
    FORMANT_MIN_ORDER,
    PHONLAB_DOCS_URL,
)
from ui.spectrogram.state.formant_settings import (
    FormantMethodState,
    FormantSettingsState,
)

M = FormantMethodState


class FormantSettingsDialog(QDialog):
    def __init__(self, settings: FormantSettingsState):
        super().__init__()

        self.setWindowTitle(self.tr("Track Formants"))
        self.setMinimumWidth(380)

        self.form = QFormLayout(self)
        self.form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.method_combo = QComboBox()
        self.method_combo.addItem(self.tr("IFC"), M.IFC.value)
        self.method_combo.addItem(self.tr("LPC"), M.LPC.value)
        self.method_combo.addItem(self.tr("RLPC (robust LPC)"), M.RLPC.value)
        self.method_combo.addItem(self.tr("TVLP (time-varying LPC)"), M.TVLP.value)
        self.method_combo.addItem(
            self.tr("DPPT (differential phase peak tracking)"), M.DPPT.value
        )
        self.method_combo.setCurrentIndex(
            self.method_combo.findData(settings.method.value)
        )
        self.form.addRow(self.tr("Method:"), self.method_combo)

        self.docs_link = QLabel()
        self.docs_link.setTextFormat(Qt.TextFormat.RichText)
        self.docs_link.setOpenExternalLinks(True)
        self.form.addRow(self.docs_link)

        self.preemphasis_spin = QDoubleSpinBox()
        self.preemphasis_spin.setRange(0.0, 1.0)
        self.preemphasis_spin.setSingleStep(0.01)
        self.preemphasis_spin.setDecimals(2)
        self.preemphasis_spin.setValue(settings.preemphasis)
        self.form.addRow(self.tr("Preemphasis:"), self.preemphasis_spin)

        self.speaker_combo = QComboBox()
        self.speaker_combo.addItem(self.tr("Long vocal tract"), FormantSpeakerType.LONG)
        self.speaker_combo.addItem(self.tr("Medium"), FormantSpeakerType.MEDIUM)
        self.speaker_combo.addItem(
            self.tr("Short vocal tract"), FormantSpeakerType.SHORT
        )
        self.speaker_combo.setCurrentIndex(
            self.speaker_combo.findData(settings.speaker)
        )
        self.form.addRow(self.tr("Speaker:"), self.speaker_combo)

        # The lowest value stands for "let phonlab choose"
        self.order_spin = QSpinBox()
        self.order_spin.setRange(FORMANT_MIN_ORDER - 1, FORMANT_MAX_ORDER)
        self.order_spin.setSpecialValueText(self.tr("Automatic"))
        self.order_spin.setValue(
            settings.order
            if settings.order >= FORMANT_MIN_ORDER
            else FORMANT_MIN_ORDER - 1
        )
        # room for "Automatic" and a little to spare
        self.order_spin.setMinimumWidth(
            self.order_spin.sizeHint().width()
            + self.order_spin.fontMetrics().horizontalAdvance("  ")
        )
        self.form.addRow(self.tr("LPC order:"), self.order_spin)

        self.top_frequency_spin = QSpinBox()
        self.top_frequency_spin.setRange(3000, 12000)
        self.top_frequency_spin.setSingleStep(500)
        self.top_frequency_spin.setSuffix(self.tr(" Hz"))
        self.top_frequency_spin.setValue(settings.top_frequency)
        self.form.addRow(self.tr("Top frequency:"), self.top_frequency_spin)

        self.median_f0_spin = QSpinBox()
        self.median_f0_spin.setRange(50, 500)
        self.median_f0_spin.setSuffix(self.tr(" Hz"))
        self.median_f0_spin.setValue(settings.median_f0)
        self.form.addRow(self.tr("Median F0:"), self.median_f0_spin)

        self.delta_f_spin = QSpinBox()
        self.delta_f_spin.setRange(500, 2000)
        self.delta_f_spin.setSingleStep(50)
        self.delta_f_spin.setSuffix(self.tr(" Hz"))
        self.delta_f_spin.setValue(settings.delta_f)
        self.form.addRow(self.tr("Formant spacing:"), self.delta_f_spin)

        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(1.0, 50.0)
        self.step_spin.setDecimals(1)
        self.step_spin.setSuffix(self.tr(" ms"))
        self.step_spin.setValue(settings.step * 1000)
        self.form.addRow(self.tr("Step:"), self.step_spin)

        self.length_spin = QDoubleSpinBox()
        self.length_spin.setRange(5.0, 200.0)
        self.length_spin.setDecimals(1)
        self.length_spin.setSuffix(self.tr(" ms"))
        self.length_spin.setValue(settings.length * 1000)
        self.form.addRow(self.tr("Window length:"), self.length_spin)

        self.voiced_check = QCheckBox(self.tr("Voiced frames only"))
        self.voiced_check.setToolTip(
            self.tr(
                "Use voice activity detection to drop formants from voiceless frames"
            )
        )
        self.voiced_check.setChecked(settings.voiced_only)
        self.form.addRow(self.voiced_check)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.0, 1.0)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setValue(settings.voicing_threshold)
        self.threshold_spin.setToolTip(
            self.tr("A frame is voiced if its probability of voicing is above this")
        )
        self.threshold_spin.setEnabled(settings.voiced_only)
        self.voiced_check.toggled.connect(self.threshold_spin.setEnabled)
        self.form.addRow(self.tr("Voicing threshold:"), self.threshold_spin)

        self.slow_warning = QLabel(
            self.tr(
                "TVLP is slower than the other methods. Tracking the whole "
                "file may take a while."
            )
        )
        self.slow_warning.setWordWrap(True)
        self.form.addRow(self.slow_warning)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.form.addRow(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        self.method_combo.currentIndexChanged.connect(self.on_method_changed)
        self.limit_to_method()

    def method(self) -> FormantMethodState:
        return FormantMethodState(self.method_combo.currentData())

    def on_method_changed(self):
        """Offer the new method's usual preemphasis and window length"""
        method_settings = FormantSettingsState().with_method(self.method())
        self.preemphasis_spin.setValue(method_settings.preemphasis)
        self.length_spin.setValue(method_settings.length * 1000)
        self.limit_to_method()

    def limit_to_method(self):
        """Show only the settings the chosen method uses"""
        method = self.method()
        shown: dict[QWidget, bool] = {
            self.speaker_combo: method == M.IFC,
            self.order_spin: method in (M.LPC, M.RLPC, M.TVLP),
            self.top_frequency_spin: method in (M.RLPC, M.TVLP),
            self.median_f0_spin: method == M.TVLP,
            self.delta_f_spin: method == M.DPPT,
            self.step_spin: method != M.IFC,  # IFC measures every 10 ms
            self.length_spin: method != M.IFC,
            self.slow_warning: method == M.TVLP,
        }
        url = PHONLAB_DOCS_URL + FORMANT_DOCS[method.value]
        self.docs_link.setText(
            self.tr("Documentation: {}").format(
                f'<a href="{url}">{self.method_combo.currentText()}</a>'
            )
        )
        for widget, visible in shown.items():
            self.form.setRowVisible(widget, visible)
        self.adjustSize()

    @staticmethod
    def open_formant_settings(
        settings: FormantSettingsState,
    ) -> FormantSettingsState | None:
        dialog = FormantSettingsDialog(settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return replace(
                settings,
                method=dialog.method(),
                preemphasis=dialog.preemphasis_spin.value(),
                speaker=dialog.speaker_combo.currentData(),
                order=dialog.chosen_order(),
                top_frequency=dialog.top_frequency_spin.value(),
                median_f0=dialog.median_f0_spin.value(),
                delta_f=dialog.delta_f_spin.value(),
                step=round(dialog.step_spin.value() / 1000, 6),
                length=round(dialog.length_spin.value() / 1000, 6),
                voiced_only=dialog.voiced_check.isChecked(),
                voicing_threshold=dialog.threshold_spin.value(),
            )
        return None

    def chosen_order(self) -> int:
        """The LPC order, or -1 for automatic"""
        value = self.order_spin.value()
        return value if value >= FORMANT_MIN_ORDER else FORMANT_AUTO_ORDER
