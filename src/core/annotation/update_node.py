from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync


class UpdateNode(UseCaseSync):
    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(self, node_id: int, time: float):
        self.annotation_repository.update_node(node_id, time)
