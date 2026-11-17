from core.annotation.entity.annotation import AnnotationLabel, AnnotationType
from core.annotation.entity.recording import Recording
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)


def recording(stem: str, talkers: list[str] | None = None) -> Recording:
    return Recording(stem, audio_file=f"{stem}.wav", talkers=talkers or [])


def test_import_creates_a_row_for_each_recording():
    repository = InMemAnnotationRepository()

    result = repository.upsert_recordings([recording("a"), recording("b")])

    assert (result.created, result.updated, result.removed) == (2, 0, 0)
    assert [r.file_stem for r in repository.list_recordings()] == ["a", "b"]


def test_importing_again_updates_rows_instead_of_duplicating_them():
    repository = InMemAnnotationRepository()
    repository.upsert_recordings([recording("a")])

    result = repository.upsert_recordings([recording("a", talkers=["t1"])])

    assert (result.created, result.updated) == (0, 1)
    assert repository.list_recordings()[0].talkers == ["t1"]


def test_recordings_that_left_the_project_are_removed_when_they_have_no_annotation():
    repository = InMemAnnotationRepository()
    repository.upsert_recordings([recording("a"), recording("b")])

    result = repository.upsert_recordings([recording("a")])

    assert result.removed == 1
    assert [r.file_stem for r in repository.list_recordings()] == ["a"]


def test_recordings_with_annotations_are_kept_even_if_they_left_the_project():
    repository = InMemAnnotationRepository()
    repository.upsert_recordings([recording("a"), recording("b")])
    b_id = repository.find_annotation_by_file_stem("b").get_id()
    repository.create_types(
        b_id, [AnnotationType("word", [AnnotationLabel(0, 0, "x")])]
    )

    result = repository.upsert_recordings([recording("a")])

    assert result.removed == 0
    assert repository.find_annotation_by_file_stem("b") is not None
