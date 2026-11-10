from core.annotation.entity.annotation import AnnotationLabel
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync


class UpdateLabel(UseCaseSync):
    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(self, label: AnnotationLabel):
        self.annotation_repository.update_label(label)
