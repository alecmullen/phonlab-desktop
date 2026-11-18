from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.word_import.state.word_import_state import WordImportState
from ui.word_import.word_import_view_model import WordImportViewModel


class WordImportDialog(QDialog):
    """Shows how a table of words lines up with the words of a tier of the project and
    what its columns will be called in the word table, and adds it to the project
    database when the user agrees. The user can save the words of the tier the table
    lacks."""

    def __init__(self, view_model: WordImportViewModel, parent: QWidget | None = None):
        super().__init__(parent)
        self.view_model = view_model
        self.state = WordImportState()
        self.result_text = ""

        self.setWindowTitle(self.tr("Add Words"))
        self.resize(720, 520)
        layout = QVBoxLayout(self)

        self.file_label = QLabel()
        layout.addWidget(self.file_label)

        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Tier that has the words:")))
        self.tier_combo = QComboBox()
        self.tier_combo.activated.connect(self.on_tier_chosen)
        row.addWidget(self.tier_combo)
        row.addStretch(1)
        layout.addLayout(row)

        self.key_label = QLabel()
        self.key_label.setWordWrap(True)
        layout.addWidget(self.key_label)

        self.match_label = QLabel()
        self.match_label.setWordWrap(True)
        self.match_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.match_label)

        self.save_button = QPushButton(self.tr("Save Unmatched Words…"))
        self.save_button.setToolTip(
            self.tr("Save the words of the project that the table lacks, as a CSV file")
        )
        self.save_button.clicked.connect(self.save_unmatched)
        layout.addWidget(self.save_button)

        layout.addWidget(QLabel(self.tr("Columns of the word table:")))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            [
                self.tr("Column"),
                self.tr("Name in the database"),
                self.tr("Type"),
                self.tr("Example"),
            ]
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.add_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if self.add_button is not None:
            self.add_button.setText(self.tr("Add Words"))
        buttons.accepted.connect(self.accept_import)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.view_model.subscribe(self.on_state)
        self.view_model.emit_state()

    @pyqtSlot(object)
    def on_state(self, state: object):
        if not isinstance(state, WordImportState):
            return
        self.state = state
        self.file_label.setText(self.tr("File: {}").format(state.file_name))
        self.tier_combo.blockSignals(True)
        self.tier_combo.clear()
        self.tier_combo.addItems(state.tiers)
        self.tier_combo.setCurrentText(state.tier)
        self.tier_combo.blockSignals(False)
        self.key_label.setText(
            self.tr(
                "The words are in the first column of the file ({}), and are "
                "compared, letter for letter, with the labels of the tier."
            ).format(state.key_column)
        )
        self.match_label.setText(self.describe_match(state))
        self.save_button.setEnabled(state.n_unmatched > 0)

        self.table.setRowCount(len(state.columns))
        for row, column in enumerate(state.columns):
            for index, value in enumerate(
                (column.source, column.name, column.sql_type, column.example)
            ):
                self.table.setItem(row, index, QTableWidgetItem(value))
        if self.add_button is not None:
            self.add_button.setEnabled(state.can_import)

    def describe_match(self, state: WordImportState) -> str:
        lines = [
            self.tr(
                "The tier has {} different words; the table has {} of them."
            ).format(state.n_words, state.n_found)
        ]
        if state.n_unmatched > 0:
            lines.append(
                self.tr(
                    "{} words of the tier are not in the table, for example: {}"
                ).format(state.n_unmatched, ", ".join(state.unmatched_examples))
            )
        if state.n_extra > 0:
            lines.append(
                self.tr("{} words of the table are not in the tier.").format(
                    state.n_extra
                )
            )
        if state.n_duplicates > 0:
            lines.append(
                self.tr(
                    "{} rows repeat a word an earlier row has, and are left out."
                ).format(state.n_duplicates)
            )
        if state.n_rows == 0:
            lines.append(self.tr("The first column of the table has no words."))
        return "\n".join(lines)

    @pyqtSlot(int)
    def on_tier_chosen(self, index: int):
        self.view_model.set_tier(self.tier_combo.itemText(index))

    def save_unmatched(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save Unmatched Words"),
            "unmatched_words.csv",
            self.tr("CSV files (*.csv)"),
        )
        if path == "":
            return
        try:
            n = self.view_model.save_unmatched(path)
        except OSError as err:
            QMessageBox.critical(self, self.tr("Save Unmatched Words"), str(err))
            return
        QMessageBox.information(
            self,
            self.tr("Save Unmatched Words"),
            self.tr("Saved {} words.").format(n),
        )

    def accept_import(self):
        try:
            result = self.view_model.import_words()
        except (ValueError, OSError) as err:
            QMessageBox.critical(self, self.tr("Add Words"), str(err))
            return
        state = self.state
        self.result_text = self.tr(
            "Made the word table with {} words and {} columns. The tier {} has {} "
            "different words; the table has {} of them."
        ).format(
            result.n_rows,
            len(result.columns),
            state.tier,
            state.n_words,
            state.n_found,
        )
        self.accept()
