from dataclasses import dataclass, field

from ui.base.state import State


@dataclass
class DatabaseViewState(State):
    """A table of the project database as the inspection window shows it"""

    tables: list[str] = field(default_factory=list)
    table: str = ""
    columns: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    filter_text: str = ""
    n_rows: int = 0  # rows in the table
    n_loaded: int = 0  # rows read from it
    n_shown: int = 0  # rows that pass the filter
