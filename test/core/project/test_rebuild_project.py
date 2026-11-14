from pathlib import Path

from support.textgrid import write_simple_textgrid

from core.annotation.entity.annotation import AnnotationType
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from core.parse_textgrid.parse_textgrid import ParseTextGrid
from core.project.add_project_files import AddProjectFiles
from core.project.entity.project_file import ProjectFile
from core.project.rebuild_project import RebuildProject


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
