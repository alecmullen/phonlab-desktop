from dataclasses import dataclass, field


@dataclass(frozen=True)
class AnnotationLabel:
    s_node: int
    e_node: int
    label: str = ""

    id: int | None = None


@dataclass(frozen=True)
class AnnotationType:
    type: str
    labels: list[AnnotationLabel]

    id: int | None = None
    # who produced the labels of this tier (the name of a talker), if it is known
    talker: str | None = None

    def get_id(self) -> int:
        if self.id is None:
            raise ValueError("AnnotationType.id is None")
        return self.id


@dataclass(frozen=True)
class Annotation:
    nodes: dict[int, float] = field(default_factory=dict)
    types: list[AnnotationType] = field(default_factory=list)

    id: int | None = None

    def get_id(self) -> int:
        if self.id is None:
            raise ValueError("Annotation.id is None")
        return self.id
