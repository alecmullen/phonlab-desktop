import dataclasses
from collections.abc import Generator

from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case import UseCase
from core.project.add_project_files import AddProjectFiles
from core.project.entity.project_file import ProjectFile
from core.project.entity.project_import_result import ProjectImportResult


class RebuildProject(UseCase[ProjectImportResult]):
    """Start a new project database and read every TextGrid into it. The previous
    database is kept as a backup, so annotation edits that were never saved to a
    TextGrid can still be recovered"""

    def __init__(
        self,
        annotation_repository: AnnotationRepository,
        add_project_files: AddProjectFiles,
    ):
        self.annotation_repository = annotation_repository
        self.add_project_files = add_project_files

    def __call__(
        self, files: list[ProjectFile]
    ) -> Generator[ProjectImportResult, None, None]:
        backup = self.annotation_repository.reset()
        for result in self.add_project_files(files):
            yield dataclasses.replace(result, backup=backup)
