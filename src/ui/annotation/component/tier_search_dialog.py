from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.annotation.state.tier_search_state import TierSearchState
from ui.annotation.tier_search_view_model import TierSearchViewModel
from ui.base.state import State


class TierSearchDialog(QDialog):
    """A movable window, left open while the user works, for finding and replacing
    label text on one tier"""

    def __init__(self, view_model: TierSearchViewModel, parent: QWidget | None = None):
        super().__init__(parent)
        self.view_model = view_model
        self.view_model.subscribe(self.on_state_change)

        self.setWindowTitle(self.tr("Search in Tier"))
        self.setWindowFlag(Qt.WindowType.Tool)
        self.setMinimumWidth(380)

        self.tier_label = QLabel()

        self.find_edit = QLineEdit()
        self.find_edit.returnPressed.connect(self.find_next)
        self.find_edit.textChanged.connect(self.update_buttons)

        self.replace_edit = QLineEdit()

        self.match_selector = QComboBox()
        self.match_selector.addItem(self.tr("Part of label"), False)
        self.match_selector.addItem(self.tr("Whole label"), True)

        self.project_checkbox = QCheckBox(self.tr("Search all files in project"))

        self.message_label = QLabel()
        self.message_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow(self.tr("Tier:"), self.tier_label)
        form.addRow(self.tr("Find:"), self.find_edit)
        form.addRow(self.tr("Replace with:"), self.replace_edit)
        form.addRow(self.tr("Match:"), self.match_selector)
        form.addRow("", self.project_checkbox)

        self.find_button = QPushButton(self.tr("Find Next"))
        self.find_button.setDefault(True)
        self.find_button.clicked.connect(self.find_next)
        self.replace_button = QPushButton(self.tr("Replace"))
        self.replace_button.clicked.connect(self.replace)
        self.replace_all_button = QPushButton(self.tr("Replace All"))
        self.replace_all_button.clicked.connect(self.replace_all)
        close_button = QPushButton(self.tr("Close"))
        close_button.clicked.connect(self.close)

        buttons = QHBoxLayout()
        buttons.addWidget(self.find_button)
        buttons.addWidget(self.replace_button)
        buttons.addWidget(self.replace_all_button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.message_label)
        layout.addLayout(buttons)

        self.update_buttons()

    @pyqtSlot(object)
    def on_state_change(self, state: State):
        if isinstance(state, TierSearchState):
            self.tier_label.setText(state.tier_name)
            self.project_checkbox.setEnabled(state.can_search_project)
            if not state.can_search_project:
                self.project_checkbox.setChecked(False)
            self.message_label.setText(state.message)

    @pyqtSlot()
    def update_buttons(self):
        has_query = self.find_edit.text() != ""
        for button in (self.find_button, self.replace_button, self.replace_all_button):
            button.setEnabled(has_query)

    def show_and_focus(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.find_edit.setFocus()
        self.find_edit.selectAll()

    def _search_options(self) -> tuple[str, bool, bool]:
        return (
            self.find_edit.text(),
            bool(self.match_selector.currentData()),
            self.project_checkbox.isChecked(),
        )

    @pyqtSlot()
    def find_next(self):
        if self.find_edit.text() != "":
            self.view_model.find_next(*self._search_options())

    @pyqtSlot()
    def replace(self):
        if self.find_edit.text() != "":
            query, exact, project = self._search_options()
            self.view_model.replace(query, self.replace_edit.text(), exact, project)

    @pyqtSlot()
    def replace_all(self):
        if self.find_edit.text() != "":
            query, exact, project = self._search_options()
            self.view_model.replace_all(query, self.replace_edit.text(), exact, project)
