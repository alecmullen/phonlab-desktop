from dataclasses import dataclass, field
from enum import Enum

from core.project.entity.project_import_result import (
    ImportStage,
    ProjectImportResult,
)
from ui.base.state import State


class ImportStageState(Enum):
    SCANNING = "scanning"
    REGISTERING = "registering"
    READING = "reading"
    INFORMATION = "information"


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
    # CSV files a rebuild added to the new database again, and those it could not
    information_applied: list[str] = field(default_factory=list)
    information_failed: list[str] = field(default_factory=list)
    stage: ImportStageState = ImportStageState.READING
    # the annotation file being read, while it is read
    current: str = ""


def to_project_import_state(result: ProjectImportResult) -> ProjectImportState:
    return ProjectImportState(
        result.done,
        result.total,
        result.registered,
        list(result.imported),
        list(result.failed),
        result.backup,
        result.finished,
        information_applied=list(result.information_applied),
        information_failed=list(result.information_failed),
        stage=ImportStageState[ImportStage(result.stage).name],
        current=result.current,
    )
