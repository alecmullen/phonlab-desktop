from core.annotation.entity.annotation import Annotation
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync


class LoadAnnotation(UseCaseSync[Annotation | None]):
    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_respository = annotation_repository

    def __call__(self, file_stem: str) -> Annotation | None:
        return self.annotation_respository.get_annotation_by_file_stem(file_stem)
