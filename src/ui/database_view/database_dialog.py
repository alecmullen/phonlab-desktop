from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.database_view.database_view_model import NULL_TEXT, DatabaseViewModel
from ui.database_view.state.database_view_state import DatabaseViewState


class DatabaseDialog(QDialog):
    """A window to look at the tables of the project database (read only), to check
    what was imported and what information was added to it"""

    def __init__(self, view_model: DatabaseViewModel, parent: QWidget | None = None):
        super().__init__(parent)
        self.view_model = view_model
        self.setWindowTitle(self.tr("Project Database"))
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(980, 560)

        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel(self.tr("Table:")))
        self.table_combo = QComboBox()
        self.table_combo.activated.connect(self.on_table_chosen)
        top.addWidget(self.table_combo)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(self.tr("Show only rows containing…"))
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textEdited.connect(self.view_model.set_filter)
        top.addWidget(self.filter_edit, 1)
        self.refresh_button = QPushButton(self.tr("Refresh"))
        self.refresh_button.clicked.connect(self.view_model.refresh)
        top.addWidget(self.refresh_button)
        layout.addLayout(top)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        self.view_model.subscribe(self.on_state)
        self.view_model.emit_state()

    @pyqtSlot(object)
    def on_state(self, state: object):
        if not isinstance(state, DatabaseViewState):
            return

        self.table_combo.blockSignals(True)
        self.table_combo.clear()
        self.table_combo.addItems(state.tables)
        self.table_combo.setCurrentText(state.table)
        self.table_combo.blockSignals(False)

        table = self.table
        table.clear()
        table.setColumnCount(len(state.columns))
        table.setRowCount(len(state.rows))
        table.setHorizontalHeaderLabels(state.columns)
        for row, values in enumerate(state.rows):
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if value == NULL_TEXT:
                    item.setForeground(Qt.GlobalColor.gray)
                table.setItem(row, column, item)
        table.resizeColumnsToContents()

        status = self.tr("{} rows").format(state.n_rows)
        if state.n_loaded < state.n_rows:
            status = self.tr("The first {} of {} rows").format(
                state.n_loaded, state.n_rows
            )
        if state.filter_text:
            status += self.tr(" — {} contain “{}”").format(
                state.n_shown, state.filter_text
            )
        self.status_label.setText(status)

    @pyqtSlot(int)
    def on_table_chosen(self, index: int):
        self.view_model.set_table(self.table_combo.itemText(index))
