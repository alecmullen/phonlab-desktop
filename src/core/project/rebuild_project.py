import dataclasses
from collections.abc import Generator

from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case import UseCase
from core.import_metadata.apply_information_sources import ApplyInformationSources
from core.project.add_project_files import AddProjectFiles
from core.project.entity.project_file import ProjectFile
from core.project.entity.project_import_result import (
    ImportStage,
    ProjectImportResult,
)


class RebuildProject(UseCase[ProjectImportResult]):
    """Start a new project database and read every TextGrid into it. The previous
    database is kept as a backup, so annotation edits that were never saved to a
    TextGrid can still be recovered.

    Given the project directory, it also adds again the information from the CSV
    files the project remembers (talkers, recordings), as the last step: the
    result that finishes the rebuild says which files were added and which could not
    be"""

    def __init__(
        self,
        annotation_repository: AnnotationRepository,
        add_project_files: AddProjectFiles,
        apply_information: ApplyInformationSources | None = None,
    ):
        self.annotation_repository = annotation_repository
        self.add_project_files = add_project_files
        self.apply_information = apply_information

    def __call__(
        self, files: list[ProjectFile], dir_path: str | None = None
    ) -> Generator[ProjectImportResult, None, None]:
        backup = self.annotation_repository.reset()

        # The finishing result is held back until the information is added, as the
        # window treats it as the end of the rebuild
        last: ProjectImportResult | None = None
        for result in self.add_project_files(files):
            if result.finished:
                last = result
            else:
                yield dataclasses.replace(result, backup=backup)
        if last is None:
            return

        information = None
        if self.apply_information is not None and dir_path is not None:
            yield ProjectImportResult(
                last.total,
                last.total,
                stage=ImportStage.INFORMATION,
                backup=backup,
            )
            information = self.apply_information(dir_path)
        yield dataclasses.replace(
            last,
            backup=backup,
            information_applied=information.applied if information else [],
            information_failed=information.failed if information else [],
        )
