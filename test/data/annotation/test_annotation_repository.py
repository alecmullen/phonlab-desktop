from pathlib import Path

import pytest

from core.annotation.entity.annotation import AnnotationLabel, AnnotationType
from data.annotation.datasource.annotation_datasource import AnnotationDataSource
from data.annotation.repository.annotation_repository import DataAnnotationRepository
from data.base.database import SQLiteDatabase


@pytest.fixture
def repository(tmp_path: Path) -> DataAnnotationRepository:
    database = SQLiteDatabase()
    database.connect(str(tmp_path))
    yield DataAnnotationRepository(AnnotationDataSource(database))
    database.engine.dispose()


def seeded_annotation(repository: DataAnnotationRepository) -> int:
    """An annotation with nodes at 0, 0.5 and 1 and one type with a label per gap"""
    id = repository.create_annotation("sample")
    nodes = repository.create_nodes(id, [0.0, 0.5, 1.0])
    first, second, third = sorted(nodes, key=nodes.get)
    repository.create_types(
        id,
        [
            AnnotationType(
                "word",
                [
                    AnnotationLabel(first, second, "a"),
                    AnnotationLabel(second, third, "b"),
                ],
            )
        ],
    )
    return id


# --------------------------- annotations ---------------------------


def test_create_annotation_returns_empty_annotation_with_id(
    repository: DataAnnotationRepository,
):
    id = repository.create_annotation("sample")

    annotation = repository.get_annotation_by_id(id)

    assert annotation.id == id
    assert annotation.nodes == {}
    assert annotation.types == []


def test_create_annotation_raises_for_duplicate_file_stem(
    repository: DataAnnotationRepository,
):
    repository.create_annotation("sample")

    with pytest.raises(ValueError):
        repository.create_annotation("sample")


def test_get_annotation_by_id_raises_for_unknown_id(
    repository: DataAnnotationRepository,
):
    with pytest.raises(ValueError):
        repository.get_annotation_by_id(99)


def test_find_annotation_by_file_stem_returns_none_when_missing(
    repository: DataAnnotationRepository,
):
    assert repository.find_annotation_by_file_stem("missing") is None


def test_find_annotation_by_file_stem_returns_stored_annotation(
    repository: DataAnnotationRepository,
):
    id = seeded_annotation(repository)

    annotation = repository.find_annotation_by_file_stem("sample")

    assert annotation is not None
    assert annotation.id == id
    assert sorted(annotation.nodes.values()) == [0.0, 0.5, 1.0]
    assert [t.type for t in annotation.types] == ["word"]
    assert [label.label for label in annotation.types[0].labels] == ["a", "b"]


# --------------------------- nodes ---------------------------


def test_create_node_adds_new_node(repository: DataAnnotationRepository):
    id = repository.create_annotation("sample")

    node_id, time = repository.create_node(id, 0.25)

    assert time == 0.25
    assert repository.get_annotation_by_id(id).nodes == {node_id: 0.25}


def test_create_node_reuses_node_within_threshold(
    repository: DataAnnotationRepository,
):
    id = repository.create_annotation("sample")
    node_id, _ = repository.create_node(id, 0.25)

    same_id, same_time = repository.create_node(id, 0.251, same_threshold=0.01)

    assert same_id == node_id
    assert same_time == 0.25
    assert len(repository.get_annotation_by_id(id).nodes) == 1


def test_create_nodes_merges_nodes_within_threshold(
    repository: DataAnnotationRepository,
):
    id = repository.create_annotation("sample")
    repository.create_nodes(id, [0.0, 1.0])

    created = repository.create_nodes(id, [0.001, 0.5], same_threshold=0.01)

    assert sorted(created.values()) == [0.0, 0.5]
    assert len(repository.get_annotation_by_id(id).nodes) == 3


def test_update_node_changes_time(repository: DataAnnotationRepository):
    id = repository.create_annotation("sample")
    node_id, _ = repository.create_node(id, 0.25)

    repository.update_node(node_id, 0.75)

    assert repository.get_annotation_by_id(id).nodes[node_id] == 0.75


def test_delete_node_removes_node(repository: DataAnnotationRepository):
    id = repository.create_annotation("sample")
    node_id, _ = repository.create_node(id, 0.25)

    repository.delete_node(node_id)

    assert repository.get_annotation_by_id(id).nodes == {}


def test_delete_nodes_if_no_labels_keeps_nodes_used_by_labels(
    repository: DataAnnotationRepository,
):
    id = seeded_annotation(repository)
    annotation = repository.get_annotation_by_id(id)
    used = {
        n for label in annotation.types[0].labels for n in (label.s_node, label.e_node)
    }
    unused_id, _ = repository.create_node(id, 5.0)

    deleted = repository.delete_nodes_if_no_labels([*used, unused_id])

    assert deleted == [unused_id]
    assert set(repository.get_annotation_by_id(id).nodes) == used


# --------------------------- labels ---------------------------


def test_create_label_returns_label_with_id(repository: DataAnnotationRepository):
    id = seeded_annotation(repository)
    annotation = repository.get_annotation_by_id(id)
    type_id = annotation.types[0].id
    start, end = sorted(annotation.nodes)[:2]

    label = repository.create_label(AnnotationLabel(start, end, "new"), type_id)

    assert label.id is not None
    assert label.label == "new"
    labels = repository.get_annotation_by_id(id).types[0].labels
    assert "new" in [stored.label for stored in labels]


def test_update_label_changes_text(repository: DataAnnotationRepository):
    id = seeded_annotation(repository)
    label = repository.get_annotation_by_id(id).types[0].labels[0]

    repository.update_label(
        AnnotationLabel(label.s_node, label.e_node, "changed", label.id)
    )

    labels = repository.get_annotation_by_id(id).types[0].labels
    assert [stored.label for stored in labels if stored.id == label.id] == ["changed"]


def test_delete_label_removes_label(repository: DataAnnotationRepository):
    id = seeded_annotation(repository)
    label = repository.get_annotation_by_id(id).types[0].labels[0]

    repository.delete_label(label)

    labels = repository.get_annotation_by_id(id).types[0].labels
    assert label.id not in [stored.id for stored in labels]
    assert len(labels) == 1


# --------------------------- clear ---------------------------


def test_clear_annotation_removes_nodes_and_types_but_keeps_stem(
    repository: DataAnnotationRepository,
):
    id = seeded_annotation(repository)

    repository.clear_annotation(id)

    cleared = repository.get_annotation_by_id(id)
    assert cleared.nodes == {}
    assert cleared.types == []
    assert repository.find_annotation_by_file_stem("sample") is not None


def test_clear_annotation_leaves_other_annotations_alone(
    repository: DataAnnotationRepository,
):
    id = seeded_annotation(repository)
    other = repository.create_annotation("other")
    repository.create_nodes(other, [0.0, 1.0])

    repository.clear_annotation(id)

    assert len(repository.get_annotation_by_id(other).nodes) == 2


def test_clear_annotation_raises_for_unknown_id(repository: DataAnnotationRepository):
    with pytest.raises(ValueError):
        repository.clear_annotation(999)
