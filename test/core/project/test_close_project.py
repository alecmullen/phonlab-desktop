from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from core.project.close_project import CloseProject


class RecordingRepository(InMemAnnotationRepository):
    def __init__(self):
        super().__init__()
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


def test_releases_the_database():
    repository = RecordingRepository()

    CloseProject(repository).run_sync()

    assert repository.closed == 1
