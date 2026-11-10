import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


def _default_filename(tab_name: str) -> str:
    base = _INVALID_FILENAME_CHARS.sub("_", tab_name).strip()
    return f"{Path(base).stem}.TextGrid"


class SaveTextGridDialog(QDialog):
    def __init__(self, origin_path: str, tab_name: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Save TextGrid"))
        self.setMinimumWidth(420)

        default_dir = Path(origin_path).parent if origin_path else Path.home()
        default_filename = _default_filename(tab_name)

        self.directory_edit = QLineEdit(str(default_dir))
        self.directory_edit.setMinimumWidth(200)
        browse_button = QPushButton(self.tr("Browse…"))
        browse_button.clicked.connect(self._browse_directory)
        dir_row = QWidget()
        dir_layout = QHBoxLayout(dir_row)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_layout.addWidget(self.directory_edit)
        dir_layout.addWidget(browse_button)

        self.filename_edit = QLineEdit(default_filename)
        self.filename_edit.setMinimumWidth(200)

        self.tg_type_selector = QComboBox()
        self.tg_type_selector.addItem("short", "short")
        self.tg_type_selector.addItem("long", "long")
        self.tg_type_selector.setCurrentIndex(0)

        form = QFormLayout()
        form.addRow(self.tr("Directory:"), dir_row)
        form.addRow(self.tr("Filename:"), self.filename_edit)
        form.addRow(self.tr("TextGrid format:"), self.tg_type_selector)

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

    def _on_accept(self):
        if (
            not self.directory_edit.text().strip()
            or not self.filename_edit.text().strip()
        ):
            QMessageBox.warning(
                self,
                self.tr("Save TextGrid"),
                self.tr("Choose a directory and filename to save to."),
            )
            return
        self.accept()

    def options(self) -> tuple[str, str]:
        path = str(
            Path(self.directory_edit.text().strip()) / self.filename_edit.text().strip()
        )
        return (path, self.tg_type_selector.currentData())

    @staticmethod
    def get_options(
        origin_path: str, tab_name: str, parent: QWidget | None = None
    ) -> tuple[str, str] | None:
        dlg = SaveTextGridDialog(origin_path, tab_name, parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.options()
        return None
