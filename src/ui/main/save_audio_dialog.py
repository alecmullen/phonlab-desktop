import re
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui.document.document_view import DocumentView

_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def _default_filename(tab_name: str) -> str:
    base = _INVALID_FILENAME_CHARS.sub("_", tab_name).strip()
    return base if base.lower().endswith(".wav") else f"{base}.wav"


@dataclass
class SaveOptions:
    path: str
    target_fs: int
    scale: bool


class SaveAudioDialog(QDialog):
    """Lets the user pick a destination, sample rate, and whether to scale
    before writing the current document's audio to disk. Always shown —
    audio edits aren't saved implicitly the way text edits often are."""

    def __init__(self, doc: DocumentView, tab_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Save Audio"))
        self.setMinimumWidth(420)

        raw_fs = doc.view_model.primary_raw_channel().fs
        default_dir = Path(doc.origin_path).parent if doc.origin_path else Path.home()
        self._default_path = str(default_dir / _default_filename(tab_name))

        self.path_edit = QLineEdit(self._default_path)
        browse_button = QPushButton(self.tr("Browse…"))
        browse_button.clicked.connect(self._browse)
        path_row = QWidget()
        path_layout = QHBoxLayout(path_row)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse_button)

        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(1000, 384000)
        self.rate_spin.setValue(raw_fs)
        self.rate_spin.setSuffix(self.tr(" Hz"))

        self.scale_check = QCheckBox(self.tr("Scale to use the full amplitude range"))
        self.scale_check.setChecked(False)

        form = QFormLayout()
        form.addRow(self.tr("Save to:"), path_row)
        form.addRow(self.tr("Sample rate:"), self.rate_spin)
        form.addRow("", self.scale_check)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _browse(self):
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save Audio"), self.path_edit.text(), self.tr("Sound files (*.wav)")
        )
        if path:
            self.path_edit.setText(path)

    def _on_accept(self):
        if not self.path_edit.text().strip():
            QMessageBox.warning(self, self.tr("Save Audio"), self.tr("Choose a file to save to."))
            return
        self.accept()

    def options(self) -> SaveOptions:
        return SaveOptions(
            path=self.path_edit.text().strip(),
            target_fs=self.rate_spin.value(),
            scale=self.scale_check.isChecked(),
        )

    @staticmethod
    def get_options(doc: DocumentView, tab_name: str, parent=None) -> SaveOptions | None:
        dlg = SaveAudioDialog(doc, tab_name, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.options()
        return None
