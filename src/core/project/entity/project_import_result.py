from dataclasses import dataclass, field


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

    @property
    def finished(self) -> bool:
        return self.done >= self.total
