from dataclasses import dataclass, field

from core.annotation.entity.metadata import MetadataTarget, SqlType


@dataclass(frozen=True)
class MetadataTable:
    """The contents of a CSV file: a header row and rows of text"""

    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)

    def column(self, header: str) -> list[str]:
        index = self.headers.index(header)
        return [row[index] for row in self.rows]


@dataclass(frozen=True)
class MetadataMatch:
    """How the rows of a table line up with the talkers or recordings of the project"""

    target: MetadataTarget
    key_column: str
    # how the key was read: "file stem", "file name", "name"...
    strategy: str
    n_rows: int = 0
    # row index -> the key (file stem or talker name) of the thing the row is about
    matches: dict[int, str] = field(default_factory=dict)
    unmatched_values: list[str] = field(default_factory=list)
    # rows that name something an earlier row already named
    n_duplicates: int = 0
    # talkers or recordings that no row names
    n_unmatched_targets: int = 0
    n_targets: int = 0
    # some of the talkers or recordings that no row names
    unmatched_targets: list[str] = field(default_factory=list)

    @property
    def n_matched(self) -> int:
        return len(self.matches)


@dataclass(frozen=True)
class MetadataColumnPlan:
    """A column of the table to add to the database"""

    source: str
    name: str
    sql_type: SqlType


@dataclass(frozen=True)
class MetadataImportResult:
    n_rows: int = 0
    columns: list[str] = field(default_factory=list)
