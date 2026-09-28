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
    QLabel,
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
    channels: list[int]


class SaveAudioDialog(QDialog):
    """Lets the user pick a destination, sample rate, and whether to scale
    before writing the current document's audio to disk. Always shown —
    audio edits aren't saved implicitly the way text edits often are."""

    def __init__(self, doc: DocumentView, tab_name: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Save Audio"))
        self.setMinimumWidth(420)

        primary_channel = doc.view_model.primary_channel()
        if primary_channel is None:
            return
        raw_fs = primary_channel.fs
        self._primary_index = doc.view_model.primary_channel_index()
        self._stereo = doc.view_model.stereo_channels() is not None

        default_dir = Path(doc.origin_path).parent if doc.origin_path else Path.home()
        default_filename = _default_filename(tab_name)

        self.directory_edit = QLineEdit(str(default_dir))
        browse_button = QPushButton(self.tr("Browse…"))
        browse_button.clicked.connect(self._browse_directory)
        dir_row = QWidget()
        dir_layout = QHBoxLayout(dir_row)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_layout.addWidget(self.directory_edit)
        dir_layout.addWidget(browse_button)

        self.filename_edit = QLineEdit(default_filename)

        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(1000, 384000)
        self.rate_spin.setValue(raw_fs)
        self.rate_spin.setSuffix(self.tr(" Hz"))

        self.scale_check = QCheckBox(self.tr("Scale to use the full amplitude range"))
        self.scale_check.setChecked(False)

        if self._stereo:
            active = doc.view_model.active_channel_indices()
            self.channel1_check = QCheckBox(self.tr("Channel 1 (Left)"))
            self.channel1_check.setChecked(0 in active)
            self.channel2_check = QCheckBox(self.tr("Channel 2 (Right)"))
            self.channel2_check.setChecked(1 in active)
            self.channel_status_label = QLabel()
            self.channel1_check.toggled.connect(self._update_channel_status)
            self.channel2_check.toggled.connect(self._update_channel_status)
            self._update_channel_status()

        form = QFormLayout()
        form.addRow(self.tr("Directory:"), dir_row)
        form.addRow(self.tr("Filename:"), self.filename_edit)
        form.addRow(self.tr("Sample rate:"), self.rate_spin)
        form.addRow("", self.scale_check)
        if self._stereo:
            form.addRow("", self.channel1_check)
            form.addRow("", self.channel2_check)
            form.addRow("", self.channel_status_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _browse_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self, self.tr("Select Directory"), self.directory_edit.text()
        )
        if directory:
            self.directory_edit.setText(directory)

    def _update_channel_status(self):
        if self.channel1_check.isChecked() and self.channel2_check.isChecked():
            self.channel_status_label.setText(self.tr("Will be saved as a stereo file"))
        elif self.channel1_check.isChecked():
            self.channel_status_label.setText(
                self.tr("Will be saved as mono (Channel 1)")
            )
        elif self.channel2_check.isChecked():
            self.channel_status_label.setText(
                self.tr("Will be saved as mono (Channel 2)")
            )
        else:
            self.channel_status_label.setText(
                self.tr("Choose at least one channel to save")
            )

    def _on_accept(self):
        if (
            not self.directory_edit.text().strip()
            or not self.filename_edit.text().strip()
        ):
            QMessageBox.warning(
                self,
                self.tr("Save Audio"),
                self.tr("Choose a directory and filename to save to."),
            )
            return
        if self._stereo and not (
            self.channel1_check.isChecked() or self.channel2_check.isChecked()
        ):
            QMessageBox.warning(
                self,
                self.tr("Save Audio"),
                self.tr("Choose at least one channel to save."),
            )
            return
        self.accept()

    def options(self) -> SaveOptions:
        path = str(
            Path(self.directory_edit.text().strip()) / self.filename_edit.text().strip()
        )
        if self._stereo:
            channels = [
                idx
                for idx, box in ((0, self.channel1_check), (1, self.channel2_check))
                if box.isChecked()
            ]
        else:
            channels = [self._primary_index]
        return SaveOptions(
            path=path,
            target_fs=self.rate_spin.value(),
            scale=self.scale_check.isChecked(),
            channels=channels,
        )

    @staticmethod
    def get_options(
        doc: DocumentView, tab_name: str, parent: QWidget | None = None
    ) -> SaveOptions | None:
        dlg = SaveAudioDialog(doc, tab_name, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.options()
        return None
