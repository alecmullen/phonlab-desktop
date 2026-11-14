from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

MAX_TIER_NAME_LENGTH = 255


class AddTiersDialog(QDialog):
    """Choose tiers to add to a file: any of the tier names already used in the
    project database, and/or a new name typed in at the bottom of the list"""

    def __init__(
        self,
        available: list[str],
        existing: list[str],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Add Tiers"))
        self.setMinimumWidth(380)

        self.existing = set(existing)

        intro = QLabel(self.tr("Choose the tiers to add to this file:"))

        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(8, 8, 8, 8)
        list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.option_checks: list[QCheckBox] = []
        for name in available:
            check = QCheckBox(name)
            if name in self.existing:
                # Already in this file: shown, so the list is the whole picture
                check.setChecked(True)
                check.setEnabled(False)
                check.setToolTip(self.tr("This file already has this tier"))
            check.toggled.connect(self._update_ok)
            list_layout.addWidget(check)
            self.option_checks.append(check)

        if len(available) == 0:
            list_layout.addWidget(
                QLabel(self.tr("No tiers in the project database yet."))
            )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.StyledPanel)
        scroll.setWidget(list_widget)
        scroll.setMinimumHeight(140)

        self.new_check = QCheckBox(self.tr("New tier:"))
        self.new_edit = QLineEdit()
        self.new_edit.setPlaceholderText(self.tr("Tier name"))
        self.new_edit.setMaxLength(MAX_TIER_NAME_LENGTH)
        new_row = QHBoxLayout()
        new_row.addWidget(self.new_check)
        new_row.addWidget(self.new_edit)
        self.new_check.toggled.connect(self._on_new_check_toggled)
        self.new_edit.textEdited.connect(self._on_new_text_edited)
        self.new_edit.textChanged.connect(self._update_ok)

        self.hint = QLabel()
        self.hint.setStyleSheet("color: #b00020;")
        self.hint.setWordWrap(True)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(scroll)
        layout.addLayout(new_row)
        layout.addWidget(self.hint)
        layout.addWidget(self.buttons)

        self._update_ok()

    def _chosen_options(self) -> list[str]:
        """The existing tier names ticked, in list order"""
        return [
            check.text()
            for check in self.option_checks
            if check.isChecked() and check.isEnabled()
        ]

    def _new_name(self) -> str:
        return self.new_edit.text().strip()

    def _on_new_text_edited(self, text: str):
        # Typing a name is asking for that tier
        if text.strip() != "" and not self.new_check.isChecked():
            self.new_check.setChecked(True)

    def _on_new_check_toggled(self, checked: bool):
        if checked and self._new_name() == "":
            self.new_edit.setFocus()
        self._update_ok()

    def problem(self) -> str | None:
        """Why the choice cannot be accepted, if it cannot"""
        if not self.new_check.isChecked():
            return None

        name = self._new_name()
        if name == "":
            return self.tr("Enter a name for the new tier.")
        if name in self.existing:
            return self.tr("This file already has a tier named {}.").format(name)
        if name in self._chosen_options():
            return self.tr("{} is already ticked in the list.").format(name)
        return None

    def _update_ok(self):
        problem = self.problem()
        has_choice = len(self._chosen_options()) > 0 or self.new_check.isChecked()

        self.hint.setText(problem or "")
        ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setEnabled(has_choice and problem is None)

    def names(self) -> list[str]:
        """The tier names to add: the ticked existing ones, then the new one"""
        names = self._chosen_options()
        if self.new_check.isChecked():
            names.append(self._new_name())
        return names

    @staticmethod
    def get_names(
        available: list[str], existing: list[str], parent: QWidget | None = None
    ) -> list[str] | None:
        dialog = AddTiersDialog(available, existing, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.names()
        return None
