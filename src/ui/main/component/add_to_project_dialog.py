from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

NEW_ANNOTATIONS = "new_annotations"
REPLACEMENT_ANNOTATIONS = "replacement_annotations"
TALKERS = "talkers"
WORDS = "words"


class AddToProjectDialog(QDialog):
    """Offers the kinds of new files that can be read into the project database"""

    @staticmethod
    def get_choice(parent: QWidget | None = None) -> str | None:
        """What the user chose to add (one of the constants above), or None if cancelled"""
        dialog = AddToProjectDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.choice()
        return None

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Add New Files"))
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(self.tr("What do you want to read into the project database?"))
        )

        self.group = QButtonGroup(self)
        self.radios: dict[str, QRadioButton] = {}
        for value, title, description in (
            (
                NEW_ANNOTATIONS,
                self.tr("New annotations"),
                self.tr(
                    "TextGrids in the project folder that are not in the database yet. "
                    "Each needs an audio file, which may be new too."
                ),
            ),
            (
                REPLACEMENT_ANNOTATIONS,
                self.tr("Replacement annotations"),
                self.tr(
                    "Choose TextGrids to read again, replacing the annotations the "
                    "database has for them. Choosing them all is like rebuilding."
                ),
            ),
            (
                TALKERS,
                self.tr("Talkers"),
                self.tr(
                    "A table with a line for each talker: the first column names the "
                    "talker, the others become columns of the talker table."
                ),
            ),
            (
                WORDS,
                self.tr("Words"),
                self.tr(
                    "A table with a line for each word, to match the words of a tier "
                    "of the annotations; its columns become a word table."
                ),
            ),
        ):
            radio = QRadioButton(title)
            self.group.addButton(radio)
            self.radios[value] = radio
            layout.addWidget(radio)
            note = QLabel(description)
            note.setWordWrap(True)
            note.setContentsMargins(24, 0, 0, 6)
            layout.addWidget(note)
        self.radios[NEW_ANNOTATIONS].setChecked(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choice(self) -> str:
        return next(value for value, radio in self.radios.items() if radio.isChecked())
