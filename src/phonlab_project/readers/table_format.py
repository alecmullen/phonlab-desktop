from dataclasses import dataclass
from enum import Enum

WHITESPACE = " "  # as a delimiter: any run of spaces


class ColumnRole(Enum):
    UNKNOWN = "unknown"
    START = "start"  # the time a label begins
    END = "end"  # the time a label ends
    LABEL = "label"  # the text of the label


class TimeUnit(Enum):
    AUTO = "auto"  # whichever makes the times fit the length of the audio
    SECONDS = "seconds"
    MILLISECONDS = "milliseconds"


@dataclass(frozen=True)
class TableFormat:
    """How to read a text file of labelled intervals as a tier: its delimiter (a tab,
    a comma or WHITESPACE), how many lines come before the first row of data, what each
    column is, and the unit of its times. With WHITESPACE the last column takes the rest
    of the line, so that a label may have spaces in it."""

    delimiter: str = WHITESPACE
    skip: int = 0
    columns: tuple[ColumnRole, ...] = ()
    unit: TimeUnit = TimeUnit.AUTO


@dataclass(frozen=True)
class TierFile:
    """A file that holds a tier of an annotation, and how to read it (None: work it
    out from the file)"""

    path: str
    table: TableFormat | None = None


@dataclass(frozen=True)
class LoadedTable:
    format: TableFormat
    names: tuple[str, ...]  # of the columns, if the line before the data gives them
    rows: list[list[str]]


@dataclass(frozen=True)
class TablePreview:
    """What a text file looks like read as a table, for the user to check"""

    format: TableFormat
    names: tuple[str, ...]
    rows: list[list[str]]  # the first rows
    n_rows: int
    unit: TimeUnit  # the unit the times are taken to be in (never AUTO)
    problem: str = ""  # why it cannot be read as a tier like this, if it cannot
