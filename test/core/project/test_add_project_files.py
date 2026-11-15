from pathlib import Path

from support.textgrid import write_simple_textgrid

from core.annotation.entity.annotation import AnnotationType
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from core.parse_textgrid.parse_textgrid import ParseTextGrid
from core.project.add_project_files import AddProjectFiles
from core.project.entity.project_file import ProjectFile
from core.project.entity.project_import_result import ProjectImportResult


def make_use_case(
    repository: InMemAnnotationRepository | None = None,
) -> tuple[AddProjectFiles, InMemAnnotationRepository]:
    repository = repository or InMemAnnotationRepository()
    return AddProjectFiles(repository, ParseTextGrid(repository)), repository


def run(use_case: AddProjectFiles, files: list[ProjectFile]) -> list:
    return list(use_case(files))


def textgrid_file(tmp_path: Path, stem: str) -> ProjectFile:
    return ProjectFile(
        stem,
        str(tmp_path / f"{stem}.wav"),
        write_simple_textgrid(tmp_path / f"{stem}.TextGrid"),
    )


def test_registers_stem_of_audio_file_without_textgrid(tmp_path: Path):
    use_case, repository = make_use_case()

    results = run(use_case, [ProjectFile("a", str(tmp_path / "a.wav"))])

    annotation = repository.find_annotation_by_file_stem("a")
    assert annotation is not None and annotation.types == []
    assert results[-1].registered == 1


def test_reads_textgrid_of_new_stem(tmp_path: Path):
    use_case, repository = make_use_case()

    results = run(use_case, [textgrid_file(tmp_path, "a")])

    annotation = repository.find_annotation_by_file_stem("a")
    assert annotation is not None
    assert [type.type for type in annotation.types] == ["word"]
    assert results[-1].imported == ["a"]


def test_reads_textgrid_of_registered_stem_with_empty_annotation(tmp_path: Path):
    use_case, repository = make_use_case()
    repository.create_annotations_if_missing(["a"])

    results = run(use_case, [textgrid_file(tmp_path, "a")])

    assert results[-1].registered == 0
    assert results[-1].imported == ["a"]
    assert len(repository.filenames) == 1


def test_does_not_read_textgrid_of_stem_that_already_has_annotation(tmp_path: Path):
    use_case, repository = make_use_case()
    id = repository.create_annotation("a")
    repository.create_types(id, [AnnotationType("mine", [])])

    results = run(use_case, [textgrid_file(tmp_path, "a")])

    annotation = repository.find_annotation_by_file_stem("a")
    assert annotation is not None
    assert [type.type for type in annotation.types] == ["mine"]
    assert results[-1].imported == []
    assert results[-1].total == 0


def test_reports_progress_after_registering_and_after_each_textgrid(tmp_path: Path):
    use_case, _ = make_use_case()
    files = [textgrid_file(tmp_path, "a"), textgrid_file(tmp_path, "b")]

    results = run(use_case, files)

    assert [(r.done, r.total) for r in results] == [(0, 2), (1, 2), (2, 2)]
    assert [r.finished for r in results] == [False, False, True]


def test_yields_a_finished_result_when_there_is_nothing_to_read(tmp_path: Path):
    use_case, _ = make_use_case()

    results = run(use_case, [ProjectFile("a", str(tmp_path / "a.wav"))])

    assert results == [ProjectImportResult(0, 0, registered=1)]
    assert results[0].finished


def test_unreadable_textgrid_is_reported_and_does_not_stop_the_others(tmp_path: Path):
    use_case, repository = make_use_case()
    bad = tmp_path / "bad.TextGrid"
    bad.write_text("not a textgrid")
    files = [
        ProjectFile("bad", str(tmp_path / "bad.wav"), str(bad)),
        textgrid_file(tmp_path, "good"),
    ]

    results = run(use_case, files)

    assert results[-1].failed == ["bad"]
    assert results[-1].imported == ["good"]
    assert results[-1].finished
    assert repository.find_annotation_by_file_stem("bad") is not None


def test_running_again_changes_nothing(tmp_path: Path):
    use_case, repository = make_use_case()
    files = [textgrid_file(tmp_path, "a")]
    run(use_case, files)
    before = repository.find_annotation_by_file_stem("a")

    results = run(use_case, files)

    assert repository.find_annotation_by_file_stem("a") == before
    assert results[-1].registered == 0
    assert results[-1].imported == []
