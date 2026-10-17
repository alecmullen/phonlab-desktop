from core.annotation.entity.annotation import Annotation
from core.base.use_case_sync import UseCaseSync


class CreateLabel(UseCaseSync[Annotation]):
    def __init__(self, annotation: Annotation, start: float, end: float):
        super().__init__()
        self.annotation = annotation
        self.start = start
        self.end = end

    def invoke(self) -> Annotation:
        return self.annotation
