from pathlib import Path

from PyQt6.QtWidgets import QInputDialog, QMessageBox, QWidget


def ask_open_with_annotation(
    parent: QWidget, audio_file: str, annotation_files: list[str]
) -> str | None:
    """Offer to open a sound file with the annotation file next to it that is named
    like it. With several, the user picks one. Returns the file to open, or None if
    the user wants the sound file alone"""
    audio_name = Path(audio_file).name
    if len(annotation_files) == 1:
        answer = QMessageBox.question(
            parent,
            parent.tr("Open Annotation"),
            parent.tr("Open {} with its annotation, {}?").format(
                audio_name, Path(annotation_files[0]).name
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        return annotation_files[0] if answer == QMessageBox.StandardButton.Yes else None

    names = [Path(path).name for path in annotation_files]
    name, accepted = QInputDialog.getItem(
        parent,
        parent.tr("Open Annotation"),
        parent.tr("Choose the annotation to open with {}:").format(audio_name),
        names,
        0,
        False,
    )
    return annotation_files[names.index(name)] if accepted else None
