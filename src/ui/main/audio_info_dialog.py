from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout

from ui.document.document_view import DocumentView


class AudioInfoDialog(QDialog):
    """Read-only summary of the current document's native (raw) audio."""

    def __init__(self, doc: DocumentView, tab_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Audio Info"))

        raw = doc.view_model.raw_wave_state
        raw_duration = len(raw.x) / raw.fs if raw.fs else 0.0

        form = QFormLayout()
        form.addRow(self.tr("Name:"), QLabel(tab_name))
        form.addRow(self.tr("Sample rate:"), QLabel(self.tr("{} Hz").format(raw.fs)))
        form.addRow(self.tr("Duration:"), QLabel(self.tr("{:.3f} s").format(raw_duration)))
        form.addRow(
            self.tr("Min / max amplitude:"),
            QLabel(self.tr("{:.4g} / {:.4g}").format(raw.min_x, raw.max_x)),
        )

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @staticmethod
    def show_info(doc: DocumentView, tab_name: str, parent=None):
        dlg = AudioInfoDialog(doc, tab_name, parent)
        dlg.exec()
