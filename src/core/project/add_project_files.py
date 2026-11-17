import dataclasses
from collections.abc import Generator

from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case import UseCase
from core.parse_textgrid.parse_textgrid import ParseTextGrid
from core.project.entity.project_file import ProjectFile
from core.project.entity.project_import_result import ProjectImportResult


class AddProjectFiles(UseCase[ProjectImportResult]):
    """Bring the project database up to date with the files in the project: add an
    entry for every file stem not yet in it, and read the TextGrid of every file whose
    annotation is empty. Annotations that already have content are never touched, so
    the database stays the source of truth once it has been built.

    Yields the progress after the stems are registered and after each TextGrid; the
    last result has done == total"""

    def __init__(
        self,
        annotation_repository: AnnotationRepository,
        parse_textgrid: ParseTextGrid,
    ):
        self.annotation_repository = annotation_repository
        self.parse_textgrid = parse_textgrid

    def __call__(
        self, files: list[ProjectFile]
    ) -> Generator[ProjectImportResult, None, None]:
        stems = [file.file_stem for file in files]
        known = {
            stem
            for stem in stems
            if self.annotation_repository.find_annotation_by_file_stem(stem) is not None
        }
        self.annotation_repository.create_annotations_if_missing(stems)

        to_read = [
            file
            for file in files
            if file.textgrid_path is not None and self._is_empty(file.file_stem)
        ]
        result = ProjectImportResult(
            total=len(to_read), registered=len(set(stems) - known)
        )
        yield result

        for file in to_read:
            imported, failed = list(result.imported), list(result.failed)
            try:
                assert file.textgrid_path is not None
                self.parse_textgrid.run_sync(file.textgrid_path, file.file_stem)
                imported.append(file.file_stem)
            except ValueError:
                # One unreadable TextGrid should not stop the others
                failed.append(file.file_stem)
            result = dataclasses.replace(
                result, done=result.done + 1, imported=imported, failed=failed
            )
            yield result

    def _is_empty(self, file_stem: str) -> bool:
        annotation = self.annotation_repository.find_annotation_by_file_stem(file_stem)
        return annotation is None or not (annotation.nodes or annotation.types)
