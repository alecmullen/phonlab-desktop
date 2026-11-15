from core.annotation.entity.annotation import Annotation, AnnotationType
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync


class AddTiersError(ValueError):
    pass


class NoTiersError(AddTiersError):
    pass


class EmptyTierNameError(AddTiersError):
    pass


class DuplicateTierNameError(AddTiersError):
    def __init__(self, name: str):
        super().__init__(name)
        self.name = name


class AddTiers(UseCaseSync[Annotation]):
    """Add empty tiers to the annotation of an audio file, whether or not it has any
    annotation yet. The tiers get no labels; they are filled in afterwards"""

    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(self, file_stem: str, names: list[str]) -> Annotation:
        if len(names) == 0:
            raise NoTiersError()

        existing = self.annotation_repository.find_annotation_by_file_stem(file_stem)
        taken = {type.type for type in existing.types} if existing else set()

        # Check everything before changing anything
        new_types: list[AnnotationType] = []
        for name in (name.strip() for name in names):
            if name == "":
                raise EmptyTierNameError()
            if name in taken:
                raise DuplicateTierNameError(name)
            taken.add(name)
            new_types.append(AnnotationType(name, []))

        if existing is None:
            annotation_id = self.annotation_repository.create_annotation(file_stem)
        else:
            annotation_id = existing.get_id()
        self.annotation_repository.create_types(annotation_id, new_types)

        return self.annotation_repository.get_annotation_by_id(annotation_id)
