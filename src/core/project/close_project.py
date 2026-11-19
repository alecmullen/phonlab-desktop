from collections.abc import Generator

from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case import UseCase


class CloseProject(UseCase[None]):
    """Release the project database, so that another project can be opened"""

    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(self) -> Generator[None, None, None]:
        self.annotation_repository.close()
        yield None
