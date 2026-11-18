from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.project_layout.project_layout_view_model import ProjectLayoutViewModel
from ui.project_layout.state.annotation_table_state import AnnotationTableState

UNKNOWN = "unknown"
MAX_SKIPPED_LINES = 100


class AnnotationTableDialog(QDialog):
    """Lets the user check how a text file with the tier of an annotation is read as a
    table: what separates its columns, how many lines come before the data, which column
    holds the start times, the end times and the labels, and the unit of the times. The
    first guess is made from the file, and the audio file it belongs to."""

    @staticmethod
    def edit(
        view_model: ProjectLayoutViewModel, index: int, parent: QWidget | None = None
    ) -> bool:
        """Asks how the files of a kind of extra file are read, and tells the view model
        the answer. Returns False if the user cancelled."""
        dialog = AnnotationTableDialog(view_model, index, parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        view_model.set_role_table(
            index,
            dialog.delimiter(),
            dialog.skip_box.value(),
            dialog.columns(),
            dialog.unit(),
            dialog.tier_name,
        )
        return True

    def __init__(
        self,
        view_model: ProjectLayoutViewModel,
        index: int,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.view_model = view_model
        self.index = index
        self.state = AnnotationTableState()
        self.role_combos: list[QComboBox] = []
        self.tier_name = ""  # the heading of the label column

        self.setWindowTitle(self.tr("Annotation File Format"))
        self.resize(760, 460)
        layout = QVBoxLayout(self)

        self.file_label = QLabel()
        layout.addWidget(self.file_label)

        controls = QHBoxLayout()
        controls.addWidget(QLabel(self.tr("Columns are separated by:")))
        self.delimiter_combo = QComboBox()
        for name, value in (
            (self.tr("spaces"), " "),
            (self.tr("tabs"), "\t"),
            (self.tr("commas"), ","),
        ):
            self.delimiter_combo.addItem(name, value)
        controls.addWidget(self.delimiter_combo)
        controls.addWidget(QLabel(self.tr("Lines before the data:")))
        self.skip_box = QSpinBox()
        self.skip_box.setRange(0, MAX_SKIPPED_LINES)
        controls.addWidget(self.skip_box)
        controls.addWidget(QLabel(self.tr("Times are in:")))
        self.unit_combo = QComboBox()
        for name, value in (
            (self.tr("whichever fits the audio"), "auto"),
            (self.tr("seconds"), "seconds"),
            (self.tr("milliseconds"), "milliseconds"),
        ):
            self.unit_combo.addItem(name, value)
        controls.addWidget(self.unit_combo)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        if header is not None:
            header.sectionDoubleClicked.connect(self.on_heading_double_clicked)
        layout.addWidget(self.table, 1)
        hint = QLabel(
            self.tr(
                "The heading of the label column is the name of the tier. "
                "Double-click it to change it."
            )
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.load(view_model.annotation_table(index), keep_tier=False)
        for signal in (
            self.delimiter_combo.activated,
            self.unit_combo.activated,
            self.skip_box.editingFinished,
        ):
            signal.connect(self.reload)

    # ------------------------------ what the user chose ------------------------------

    def delimiter(self) -> str:
        return self.delimiter_combo.currentData()

    def unit(self) -> str:
        return self.unit_combo.currentData()

    def columns(self) -> list[str]:
        return [combo.currentData() for combo in self.role_combos]

    # ------------------------------ showing ------------------------------

    def reload(self, _index: int = 0):
        """Reads the file again with the delimiter, lines to skip and unit chosen"""
        self.load(
            self.view_model.annotation_table(
                self.index, self.delimiter(), self.skip_box.value(), self.unit()
            ),
            keep_tier=True,
        )

    def load(self, state: AnnotationTableState, keep_tier: bool):
        self.state = state
        if not keep_tier:
            self.tier_name = state.tier
        self.file_label.setText(
            self.tr("How {} is read as a table of labelled intervals:").format(
                state.file_name
            )
        )
        for widget, value in (
            (self.delimiter_combo, state.delimiter),
            (self.unit_combo, state.unit),
        ):
            widget.setCurrentIndex(max(widget.findData(value), 0))
        self.skip_box.setValue(state.skip)
        self._fill_table(state)
        self._show_status(state)

    def _fill_table(self, state: AnnotationTableState):
        n_columns = len(state.columns)
        table = self.table
        table.clear()
        table.setColumnCount(n_columns)
        table.setRowCount(len(state.rows) + 1)
        table.setVerticalHeaderLabels(
            [self.tr("is"), *[str(i + 1) for i in range(len(state.rows))]]
        )

        self.role_combos = []
        for column, role in enumerate(state.columns):
            combo = QComboBox()
            for name, value in (
                (self.tr("Unknown (ignore)"), UNKNOWN),
                (self.tr("Start time"), "start"),
                (self.tr("End time"), "end"),
                (self.tr("Label"), "label"),
            ):
                combo.addItem(name, value)
            combo.setCurrentIndex(max(combo.findData(role), 0))
            combo.activated.connect(
                lambda _, column=column: self.on_role_chosen(column)
            )
            table.setCellWidget(0, column, combo)
            self.role_combos.append(combo)
        for row, values in enumerate(state.rows, start=1):
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row, column, item)
        self._show_headings()
        table.resizeColumnsToContents()

    def _show_headings(self):
        """The heading of each column is what the file calls it, or its number; the
        label column's is the name of the tier"""
        names = self.state.names
        headings = []
        for column, combo in enumerate(self.role_combos):
            if combo.currentData() == "label":
                headings.append(self.tier_name)
            elif column < len(names):
                headings.append(names[column])
            else:
                headings.append(self.tr("Column {}").format(column + 1))
        self.table.setHorizontalHeaderLabels(headings)
        self.table.resizeColumnsToContents()

    def on_heading_double_clicked(self, column: int):
        if column < len(self.role_combos) and (
            self.role_combos[column].currentData() == "label"
        ):
            name, accepted = QInputDialog.getText(
                self,
                self.tr("Tier Name"),
                self.tr("Name of the tier:"),
                text=self.tier_name,
            )
            if accepted:
                self.rename_tier(name)

    def rename_tier(self, name: str):
        if name.strip() != "":
            self.tier_name = name.strip()
            self._show_headings()

    def on_role_chosen(self, column: int):
        """A role is held by one column: choosing it for this one frees the other"""
        role = self.role_combos[column].currentData()
        if role != UNKNOWN:
            for other, combo in enumerate(self.role_combos):
                if other != column and combo.currentData() == role:
                    combo.setCurrentIndex(combo.findData(UNKNOWN))
        self._show_headings()
        self._show_status(
            self.view_model.annotation_table(
                self.index,
                self.delimiter(),
                self.skip_box.value(),
                self.unit(),
                self.columns(),
            )
        )

    def _show_status(self, state: AnnotationTableState):
        if state.problem:
            self.status_label.setStyleSheet("color: #b00020;")
            self.status_label.setText(state.problem)
        else:
            self.status_label.setStyleSheet("")
            self.status_label.setText(
                self.tr("{} labels, with times in {}.").format(
                    state.n_rows, self._unit_name(state.unit_used)
                )
            )
        if self.ok_button is not None:
            self.ok_button.setEnabled(state.problem == "")

    def _unit_name(self, unit: str) -> str:
        return self.tr("milliseconds") if unit == "milliseconds" else self.tr("seconds")
