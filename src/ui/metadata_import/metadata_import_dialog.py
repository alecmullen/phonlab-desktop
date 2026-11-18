from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.annotation.entity.metadata import MetadataTarget
from ui.metadata_import.metadata_import_view_model import MetadataImportViewModel
from ui.metadata_import.state.metadata_import_state import MetadataImportState

INFO_TEXT = """
<p>A CSV file with information about <b>talkers</b> should have one row per talker.
A CSV file with information about <b>recordings</b> should have one row per
recording.</p>
<p>The first row should have a column header: a short name for the information in
that column.</p>
<p>For example, a talker CSV might have a column called "talker", which should match
the talker information inferred from the file names and/or folders of the project,
and then columns for 'age', 'race', 'gender', etc.</p>
<p>A recording CSV needs a column that names each recording, by its file name or by
its path in the project, and then columns for what is true of each recording, such
as 'speech_rate' or 'condition'.</p>
<p>Upper and lower case do not matter when matching. Rows that match nothing are
listed and left out. Adding a file again with the same column names updates the
values. Empty cells stay empty.</p>
"""


class MetadataImportDialog(QDialog):
    """Adds columns from a CSV file to the talkers or the recordings of the project"""

    def __init__(
        self, view_model: MetadataImportViewModel, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.view_model = view_model
        self.state = MetadataImportState()
        self.result_text = ""
        self._built = False

        self.setWindowTitle(self.tr("Add Information from CSV"))
        self.resize(760, 560)
        layout = QVBoxLayout(self)

        self.file_label = QLabel()
        layout.addWidget(self.file_label)

        about = self.about_group = QGroupBox(self.tr("What is each row about?"))
        about_layout = QHBoxLayout(about)
        self.talkers_radio = QRadioButton(self.tr("Information about talkers"))
        self.recordings_radio = QRadioButton(self.tr("Information about recordings"))
        self.talkers_radio.toggled.connect(self.on_target_toggled)
        about_layout.addWidget(self.talkers_radio)
        about_layout.addWidget(self.recordings_radio)
        about_layout.addStretch(1)
        self.info_button = QToolButton()
        self.info_button.setText("i")
        self.info_button.setToolTip(self.tr("How to prepare the CSV file"))
        self.info_button.setStyleSheet(
            "QToolButton { border: 1px solid gray; border-radius: 9px; "
            "min-width: 18px; max-width: 18px; min-height: 18px; max-height: 18px; "
            "font-weight: bold; font-style: italic; }"
        )
        self.info_button.clicked.connect(self.show_info)
        about_layout.addWidget(self.info_button)
        layout.addWidget(about)

        key_row = QHBoxLayout()
        self.key_label = QLabel()
        key_row.addWidget(self.key_label)
        self.key_combo = QComboBox()
        self.key_combo.activated.connect(self.on_key_chosen)
        key_row.addWidget(self.key_combo, 1)
        layout.addLayout(key_row)

        self.match_label = QLabel()
        self.match_label.setWordWrap(True)
        self.match_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.match_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            [
                self.tr("Add"),
                self.tr("Column in the file"),
                self.tr("Name in the database"),
                self.tr("Type"),
                self.tr("Example"),
            ]
        )
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.add_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if self.add_button is not None:
            self.add_button.setText(self.tr("Add"))
        self.button_box.accepted.connect(self.accept_import)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.view_model.subscribe(self.on_state)
        self.view_model.emit_state()

    # ------------------------------ state ------------------------------

    @pyqtSlot(object)
    def on_state(self, state: object):
        if not isinstance(state, MetadataImportState):
            return
        self.state = state
        self.file_label.setText(self.tr("File: {}").format(state.file_name))
        self.about_group.setVisible(not state.target_locked)
        if state.target_locked:
            self.setWindowTitle(
                self.tr("Add Talkers")
                if state.target == MetadataTarget.TALKER.value
                else self.tr("Add Information about Recordings")
            )

        for radio, checked in (
            (self.talkers_radio, state.target == MetadataTarget.TALKER.value),
            (self.recordings_radio, state.target == MetadataTarget.RECORDING.value),
        ):
            radio.blockSignals(True)
            radio.setChecked(checked)
            radio.blockSignals(False)

        self.key_label.setText(
            self.tr("Column that names the talkers:")
            if state.target == MetadataTarget.TALKER.value
            else self.tr("Column that names the recordings:")
        )
        self.key_combo.blockSignals(True)
        self.key_combo.clear()
        self.key_combo.addItems(state.key_columns)
        self.key_combo.setCurrentText(state.key_column)
        self.key_combo.blockSignals(False)

        self._show_match(state)
        self._show_columns(state)
        if self.add_button is not None:
            self.add_button.setEnabled(state.can_import)

    def _show_match(self, state: MetadataImportState):
        what = (
            self.tr("talkers")
            if state.target == MetadataTarget.TALKER.value
            else self.tr("recordings")
        )
        lines = [
            self.tr("{} of {} rows match {} of the project ({}).").format(
                state.n_matched, state.n_rows, what, state.strategy
            )
        ]
        if state.n_unmatched_targets:
            lines.append(
                self.tr("{} of {} {} have no row in the file, for example: {}").format(
                    state.n_unmatched_targets,
                    state.n_targets,
                    what,
                    ", ".join(state.unmatched_target_examples),
                )
            )
        if state.n_duplicates:
            lines.append(
                self.tr(
                    "{} rows repeat one named earlier; the last one is used."
                ).format(state.n_duplicates)
            )
        if state.unmatched_examples:
            lines.append(
                self.tr("Rows left out, for example: {}").format(
                    ", ".join(state.unmatched_examples)
                )
            )
        self.match_label.setStyleSheet(
            "color: #b00020;" if state.n_matched == 0 else ""
        )
        self.match_label.setText("\n".join(lines))

    def _show_columns(self, state: MetadataImportState):
        table = self.table
        shown = [
            item.text() if (item := table.item(row, 1)) is not None else ""
            for row in range(table.rowCount())
        ]
        same = shown == [column.source for column in state.columns]
        if not same:
            table.setRowCount(len(state.columns))
            for row, column in enumerate(state.columns):
                check = QCheckBox()
                check.toggled.connect(
                    lambda checked, source=column.source: (
                        self.view_model.set_column_selected(source, checked)
                    )
                )
                table.setCellWidget(row, 0, check)
                table.setItem(row, 1, QTableWidgetItem(column.source))
                edit = QLineEdit()
                edit.editingFinished.connect(
                    lambda source=column.source, edit=edit: (
                        self.view_model.set_column_name(source, edit.text())
                    )
                )
                table.setCellWidget(row, 2, edit)

        for row, column in enumerate(state.columns):
            check = table.cellWidget(row, 0)
            edit = table.cellWidget(row, 2)
            if isinstance(check, QCheckBox):
                check.blockSignals(True)
                check.setChecked(column.selected)
                check.blockSignals(False)
            if isinstance(edit, QLineEdit) and not edit.hasFocus():
                edit.setText(column.name)
            table.setItem(row, 3, QTableWidgetItem(column.sql_type))
            table.setItem(row, 4, QTableWidgetItem(column.example))

    # ------------------------------ actions ------------------------------

    @pyqtSlot(bool)
    def on_target_toggled(self, talkers_checked: bool):
        self.view_model.set_target(
            MetadataTarget.TALKER.value
            if talkers_checked
            else MetadataTarget.RECORDING.value
        )

    @pyqtSlot(int)
    def on_key_chosen(self, index: int):
        self.view_model.set_key_column(self.key_combo.itemText(index))

    def show_info(self):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle(self.tr("Information from a CSV file"))
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(self.tr(INFO_TEXT))
        box.exec()

    def accept_import(self):
        n_left_out = self.state.n_rows - self.state.n_matched
        if n_left_out > 0:
            answer = QMessageBox.question(
                self,
                self.tr("Add Information from CSV"),
                self.tr(
                    "{} of the {} rows in the file match nothing in the project and "
                    "will be left out. Add the information for the other rows?"
                ).format(n_left_out, self.state.n_rows),
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            result = self.view_model.import_information()
        except Exception as err:  # noqa: BLE001
            QMessageBox.critical(self, self.tr("Add Information from CSV"), str(err))
            return
        what = (
            self.tr("talkers")
            if self.state.target == MetadataTarget.TALKER.value
            else self.tr("recordings")
        )
        self.result_text = self.tr("Added {} columns ({}) to {} {}.").format(
            len(result.columns), ", ".join(result.columns), result.n_rows, what
        )
        self.accept()
