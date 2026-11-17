from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TableData:
    """The first rows of a table of the project database, to look at"""

    name: str
    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    # how many rows the table has, which may be more than `rows` holds
    n_rows: int = 0
