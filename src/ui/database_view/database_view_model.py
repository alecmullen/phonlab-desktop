from typing import Any

from core.inspect_database.entity.table_data import TableData
from core.inspect_database.inspect_database import ListTables, ReadTable
from res.constants import DATABASE_VIEW_ROW_LIMIT
from ui.base.view_model import ViewModel
from ui.database_view.state.database_view_state import DatabaseViewState

NULL_TEXT = "NULL"


class DatabaseViewModel(ViewModel):
    """Lets the user look at the tables of the project database, read only"""

    def __init__(self, list_tables: ListTables, read_table: ReadTable):
        super().__init__()
        self.list_tables = list_tables
        self.read_table = read_table

        self.tables: list[str] = []
        self.data = TableData("")
        self.filter_text = ""

    def prepare(self):
        self.tables = self.list_tables()
        self.data = TableData(self.tables[0]) if self.tables else TableData("")
        self.refresh()

    def refresh(self):
        """Reads the current table again, for example after adding information"""
        self.tables = self.list_tables()
        if self.data.name in self.tables:
            self.data = self.read_table(self.data.name, DATABASE_VIEW_ROW_LIMIT)
        self.emit_state()

    def set_table(self, name: str):
        self.data = self.read_table(name, DATABASE_VIEW_ROW_LIMIT)
        self.emit_state()

    def set_filter(self, text: str):
        self.filter_text = text
        self.emit_state()

    def emit_state(self):
        self.state_changed.emit(self.to_state())

    def to_state(self) -> DatabaseViewState:
        rows = [[_text(value) for value in row] for row in self.data.rows]
        needle = self.filter_text.strip().casefold()
        if needle:
            rows = [
                row for row in rows if any(needle in cell.casefold() for cell in row)
            ]
        return DatabaseViewState(
            tables=list(self.tables),
            table=self.data.name,
            columns=list(self.data.columns),
            rows=rows,
            filter_text=self.filter_text,
            n_rows=self.data.n_rows,
            n_loaded=len(self.data.rows),
            n_shown=len(rows),
        )


def _text(value: Any) -> str:  # noqa: ANN401
    return NULL_TEXT if value is None else str(value)
