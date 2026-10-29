from core.annotation.entity.annotation import Annotation
from core.annotation.repository.annotation_repository import AnnotationRepository
from data.annotation.datasource.annotation_datasource import AnnotationDataSource
from data.annotation.mapping.annotation_mapping import annotation_to_entity


class AnnotationRepositoryImpl(AnnotationRepository):
    def __init__(self, local_datasource: AnnotationDataSource):
        self.local_datasource = local_datasource

    def save_annotation(self, annotation: Annotation):
        entity = annotation_to_entity(annotation)
        self.local_datasource.save_annotation(entity)
