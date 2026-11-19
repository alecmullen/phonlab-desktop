from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QLabel,
    QLineEdit,
    QListView,
    QWidget,
)


class OpenPathDialog(QFileDialog):
    """File dialog to open either a project directory or sound and TextGrid files.

    A file dialog normally navigates into a selected directory rather than choosing
    it, so this one accepts a directory when it is the only thing selected. It is
    not the native dialog because the native ones choose files or directories, never
    both"""

    def __init__(
        self,
        parent: QWidget | None = None,
        caption: str = "",
        directory: str = "",
        filter: str = "",
    ):
        super().__init__(parent, caption, directory, filter)
        self.setFileMode(QFileDialog.FileMode.ExistingFiles)
        self.setOption(QFileDialog.Option.DontUseNativeDialog)

        # The filter still lists only the files that can be opened, but there is
        # nothing to choose from, so leave out the box to pick one
        for name, type in (("fileTypeCombo", QComboBox), ("fileTypeLabel", QLabel)):
            widget = self.findChild(type, name)
            if widget is not None:
                widget.hide()

        # Name the box after what is selected: a directory is a project
        self.name_label = self.findChild(QLabel, "fileNameLabel")
        self.name_edit = self.findChild(QLineEdit, "fileNameEdit")
        self.file_label_text = self.name_label.text() if self.name_label else ""
        self.project_label_text = self.tr("&Project:")
        list_view = self.findChild(QListView, "listView")
        selection_model = list_view.selectionModel() if list_view else None
        if selection_model is not None:
            selection_model.selectionChanged.connect(self.show_selection)

    def show_selection(self):
        """Show a selected directory in the name box, which Qt leaves blank for one"""
        selected = self.selectedFiles()
        project = len(selected) == 1 and Path(selected[0]).is_dir()
        if self.name_label is not None:
            self.name_label.setText(
                self.project_label_text if project else self.file_label_text
            )
        if project and self.name_edit is not None:
            name = Path(selected[0]).name
            if self.name_edit.text() != name:
                self.name_edit.setText(name)

    def accept(self):
        selected = self.selectedFiles()
        if len(selected) == 1 and Path(selected[0]).is_dir():
            QDialog.accept(self)
        else:
            super().accept()

    @staticmethod
    def get_paths(
        parent: QWidget | None = None,
        caption: str = "",
        directory: str | None = None,
        filter: str = "",
    ) -> list[str]:
        """The directory or the files the user chose, empty if they cancelled"""
        dialog = OpenPathDialog(parent, caption, directory or "", filter)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return []
        return dialog.selectedFiles()
