from pathlib import Path

from PyQt6.QtWidgets import QMessageBox, QWidget


def ask_overwrite_annotation(
    parent: QWidget, annotation_file: str, allow_all: bool = False
) -> QMessageBox.StandardButton:
    """Ask whether to replace the annotation already in the project database with the
    one in annotation_file. With allow_all, also offers "Yes to All" and "No to All"
    for when several files are being loaded. The default answer is No"""
    buttons = QMessageBox.StandardButton
    options = buttons.Yes | buttons.No
    if allow_all:
        options = buttons.Yes | buttons.YesToAll | buttons.No | buttons.NoToAll
    return QMessageBox.question(
        parent,
        parent.tr("Overwrite Annotation"),
        parent.tr("Overwrite the existing database with annotation from {}?").format(
            Path(annotation_file).name
        ),
        options,
        buttons.No,
    )
