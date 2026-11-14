from dataclasses import dataclass, field

from core.project.entity.project_import_result import ProjectImportResult
from ui.base.state import State


@dataclass
class ProjectImportState(State):
    """Progress of adding files to the project database. done and total count the
    TextGrids being read; error is set if the import stopped with a failure"""

    done: int = 0
    total: int = 0
    registered: int = 0
    imported: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    backup: str | None = None
    finished: bool = False
    error: str | None = None


def to_project_import_state(result: ProjectImportResult) -> ProjectImportState:
    return ProjectImportState(
        result.done,
        result.total,
        result.registered,
        list(result.imported),
        list(result.failed),
        result.backup,
        result.finished,
    )
