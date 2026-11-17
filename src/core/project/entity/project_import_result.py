from dataclasses import dataclass, field
from enum import Enum


class ImportStage(Enum):
    SCANNING = "scanning"  # looking through the project's files
    REGISTERING = "registering"  # recording the files in the database
    READING = "reading"  # reading the annotation files
    INFORMATION = "information"  # adding information from CSV files


@dataclass(frozen=True)
class ProjectImportResult:
    """Progress of adding files to the project database. done and total count the
    TextGrids to read; the import is finished when done == total"""

    done: int = 0
    total: int = 0
    registered: int = 0  # file stems newly added to the database
    imported: list[str] = field(default_factory=list)  # stems whose TextGrid was read
    failed: list[str] = field(default_factory=list)  # stems whose TextGrid was not read
    backup: str | None = None  # where a rebuild saved the previous database
    # CSV files whose information a rebuild added to the new database again, and
    # those that could not be added
    information_applied: list[str] = field(default_factory=list)
    information_failed: list[str] = field(default_factory=list)
    stage: ImportStage = ImportStage.READING
    # the annotation file being read, while it is read
    current: str = ""

    @property
    def finished(self) -> bool:
        return self.stage is ImportStage.READING and self.done >= self.total
