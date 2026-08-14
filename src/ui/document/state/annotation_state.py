from dataclasses import dataclass


@dataclass(Frozen=True)
class AnnotationState:
    layers: int = 0
    