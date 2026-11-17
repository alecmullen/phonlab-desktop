from dataclasses import dataclass
from enum import StrEnum


class MetadataTarget(StrEnum):
    """What a row of added information is about"""

    TALKER = "talker"
    RECORDING = "recording"


class SqlType(StrEnum):
    INTEGER = "INTEGER"
    REAL = "REAL"
    TEXT = "TEXT"


@dataclass(frozen=True)
class MetadataColumn:
    """A column of information the user added to the project database. `name`
    contains only letters, digits and underscores."""

    name: str
    sql_type: SqlType = SqlType.TEXT
