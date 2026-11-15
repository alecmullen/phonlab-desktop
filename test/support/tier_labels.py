"""A small project of annotations for exercising tier search"""

from core.annotation.entity.annotation import AnnotationLabel, AnnotationType
from core.annotation.repository.annotation_repository import AnnotationRepository


def add_file(
    repository: AnnotationRepository,
    file_stem: str,
    tiers: dict[str, list[str]],
) -> int:
    """Adds a file whose tiers hold the given label texts, each label one second
    long and following the last on its tier"""
    id = repository.create_annotation(file_stem)
    longest = max(len(labels) for labels in tiers.values())
    nodes = repository.create_nodes(id, [float(t) for t in range(longest + 1)], 0.1)
    node_ids = sorted(nodes, key=nodes.get)
    repository.create_types(
        id,
        [
            AnnotationType(
                name,
                [
                    AnnotationLabel(node_ids[i], node_ids[i + 1], text)
                    for i, text in enumerate(labels)
                ],
            )
            for name, labels in tiers.items()
        ],
    )
    return id


def populate_project(repository: AnnotationRepository):
    add_file(repository, "a", {"word": ["cat", "dog", "cats"], "phone": ["k", "ae"]})
    add_file(repository, "b", {"word": ["bird", "cat"]})
    add_file(repository, "sub/c", {"word": ["dog"]})
