from pathlib import Path
from typing import cast

from support.textgrid import write_simple_textgrid

from core.annotation.entity.annotation import AnnotationType
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from core.import_metadata.apply_information_sources import ApplyInformationSources
from core.import_metadata.entity.information_source import AppliedInformation
from core.parse_textgrid.parse_textgrid import ParseTextGrid
from core.project.add_project_files import AddProjectFiles
from core.project.rebuild_project import RebuildProject
from phonlab_project.layout.project_file import ProjectFile


def make_use_case() -> tuple[RebuildProject, InMemAnnotationRepository]:
    repository = InMemAnnotationRepository()
    add_project_files = AddProjectFiles(repository, ParseTextGrid(repository))
    return RebuildProject(repository, add_project_files), repository


def test_replaces_database_content_with_the_textgrids(tmp_path: Path):
    use_case, repository = make_use_case()
    id = repository.create_annotation("a")
    repository.create_types(id, [AnnotationType("edited", [])])
    repository.create_annotation("removed")
    file = ProjectFile(
        "a", str(tmp_path / "a.wav"), write_simple_textgrid(tmp_path / "a.TextGrid")
    )

    results = list(use_case([file]))

    annotation = repository.find_annotation_by_file_stem("a")
    assert annotation is not None
    assert [type.type for type in annotation.types] == ["word"]
    assert repository.find_annotation_by_file_stem("removed") is None
    assert results[-1].imported == ["a"] and results[-1].finished


class BackingUpRepository(InMemAnnotationRepository):
    def reset(self) -> str | None:
        super().reset()
        return "/some/phonlab.bak"


def test_reports_where_the_old_database_was_backed_up(tmp_path: Path):
    repository = BackingUpRepository()
    use_case = RebuildProject(
        repository, AddProjectFiles(repository, ParseTextGrid(repository))
    )

    results = list(use_case([ProjectFile("a", str(tmp_path / "a.wav"))]))

    assert all(result.backup == "/some/phonlab.bak" for result in results)


# --------------------------- information from CSV files ---------------------------


class FakeApplyInformation:
    def __init__(self, applied: list[str], failed: list[str]):
        self.applied, self.failed = applied, failed
        self.called_with: list[str] = []

    def __call__(self, dir_path: str) -> AppliedInformation:
        self.called_with.append(dir_path)
        return AppliedInformation(self.applied, self.failed)


def make_use_case_with_information(
    applied: list[str], failed: list[str]
) -> tuple[RebuildProject, FakeApplyInformation, InMemAnnotationRepository]:
    repository = InMemAnnotationRepository()
    apply = FakeApplyInformation(applied, failed)
    return (
        RebuildProject(
            repository,
            AddProjectFiles(repository, ParseTextGrid(repository)),
            cast(ApplyInformationSources, apply),
        ),
        apply,
        repository,
    )


def test_the_finishing_result_says_which_information_was_added_again(tmp_path: Path):
    use_case, apply, _ = make_use_case_with_information(["a.csv"], ["b.csv"])
    file = ProjectFile(
        "a", str(tmp_path / "a.wav"), write_simple_textgrid(tmp_path / "a.TextGrid")
    )

    results = list(use_case([file], str(tmp_path)))

    assert apply.called_with == [str(tmp_path)]
    *earlier, last = results
    assert last.finished
    assert (last.information_applied, last.information_failed) == (["a.csv"], ["b.csv"])
    assert all(result.information_applied == [] for result in earlier)
    assert not any(result.finished for result in earlier)


def test_information_is_added_after_the_textgrids_are_read(tmp_path: Path):
    use_case, _, repository = make_use_case_with_information([], [])
    seen_at_apply: list[list[str]] = []
    use_case.apply_information = cast(
        ApplyInformationSources,
        lambda dir_path: (
            seen_at_apply.append(sorted(repository.filenames.values()))
            or AppliedInformation()
        ),
    )
    file = ProjectFile("a", str(tmp_path / "a.wav"))

    list(use_case([file], str(tmp_path)))

    assert seen_at_apply == [["a"]]  # the database was already filled


def test_without_a_project_directory_no_information_is_added(tmp_path: Path):
    use_case, apply, _ = make_use_case_with_information(["a.csv"], [])

    results = list(use_case([ProjectFile("a", str(tmp_path / "a.wav"))]))

    assert apply.called_with == []
    assert results[-1].information_applied == []


def test_progress_is_passed_on_as_it_happens_and_the_information_step_is_announced(
    tmp_path: Path,
):
    use_case, _, _ = make_use_case_with_information([], [])
    file = ProjectFile(
        "a", str(tmp_path / "a.wav"), write_simple_textgrid(tmp_path / "a.TextGrid")
    )

    results = list(use_case([file], str(tmp_path)))

    assert [(r.stage.value, r.current) for r in results] == [
        ("registering", ""),
        ("reading", ""),
        ("reading", "a.TextGrid"),
        ("information", ""),
        ("reading", ""),
    ]
    assert [r.finished for r in results] == [False] * 4 + [True]
