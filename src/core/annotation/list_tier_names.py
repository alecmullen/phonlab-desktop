from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync


class ListTierNames(UseCaseSync[list[str]]):
    """The tier names used in the project database, to offer when adding tiers"""

    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(self) -> list[str]:
        return self.annotation_repository.list_tier_names()
