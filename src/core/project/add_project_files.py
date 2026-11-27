import dataclasses
from collections.abc import Generator
from pathlib import Path

from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case import UseCase
from core.parse_textgrid.parse_textgrid import ParseTextGrid
from core.project.entity.project_import_result import (
    ImportStage,
    ProjectImportResult,
)
from phonlab_project.layout.project_file import ProjectFile


class AddProjectFiles(UseCase[ProjectImportResult]):
    """Bring the project database up to date with the files in the project: add an
    entry for every file stem not yet in it, record what the project's layout says
    about each recording, and read the TextGrid of every file whose annotation is
    empty. Annotations that already have content are never touched, so the database
    stays the source of truth once it has been built.

    Yields the progress when it starts registering the files, after they are
    registered, before each TextGrid is read (saying which) and after it; the last
    result has done == total"""

    def __init__(
        self,
        annotation_repository: AnnotationRepository,
        parse_textgrid: ParseTextGrid,
    ):
        self.annotation_repository = annotation_repository
        self.parse_textgrid = parse_textgrid

    def __call__(
        self, files: list[ProjectFile], replace: bool = False
    ) -> Generator[ProjectImportResult, None, None]:
        """With `replace`, the annotations of `files` are read again even if the
        database has them, and replace what it has; nothing else in the database is
        touched, so `files` may be some of the project's files."""
        yield ProjectImportResult(stage=ImportStage.REGISTERING)

        stems = [file.file_stem for file in files]
        known = {
            stem
            for stem in stems
            if self.annotation_repository.find_annotation_by_file_stem(stem) is not None
        }
        self.annotation_repository.create_annotations_if_missing(stems)

        # What the project's layout says about each recording (talkers, extra files,
        # channels...) is kept next to its annotation. Recordings that left the
        # project and have no annotation content are dropped, so the database
        # follows the layout.
        recordings = [file.recording for file in files if file.recording is not None]
        if recordings:
            self.annotation_repository.upsert_recordings(
                recordings,
                remove_others=not replace and len(recordings) == len(files),
            )

        to_read = [
            file
            for file in files
            if (file.textgrid_path is not None or file.tier_files)
            and (replace or self._is_empty(file.file_stem))
        ]
        result = ProjectImportResult(
            total=len(to_read), registered=len(set(stems) - known)
        )
        yield result

        for file in to_read:
            current = file.textgrid_path or next(iter(file.tier_files.values())).path
            yield dataclasses.replace(result, current=Path(current).name)

            imported, failed = list(result.imported), list(result.failed)
            try:
                self.parse_textgrid.run_sync(
                    file.textgrid_path,
                    file.file_stem,
                    overwrite=replace,
                    tier_files=file.tier_files,
                    audio_path=file.audio_path,
                )
                imported.append(file.file_stem)
            except ValueError:
                # One unreadable TextGrid should not stop the others
                failed.append(file.file_stem)
            result = dataclasses.replace(
                result,
                done=result.done + 1,
                imported=imported,
                failed=failed,
                current="",
            )
            yield result

    def _is_empty(self, file_stem: str) -> bool:
        annotation = self.annotation_repository.find_annotation_by_file_stem(file_stem)
        return annotation is None or not (annotation.nodes or annotation.types)
