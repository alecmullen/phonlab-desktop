from dataclasses import dataclass, field

from ui.base.state import State


@dataclass
class AnnotationTableState(State):
    """A text file of an annotation read as a table, for the user to check. The roles
    of the columns are "start", "end", "label" and "unknown"; the unit is "auto",
    "seconds" or "milliseconds"; the delimiter is "\\t", "," or " " (spaces)."""

    file_name: str = ""
    tier: str = ""  # the name of the tier: the heading of the label column
    delimiter: str = " "
    skip: int = 0
    unit: str = "auto"
    unit_used: str = "seconds"  # what "auto" came to
    columns: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    n_rows: int = 0
    problem: str = ""
