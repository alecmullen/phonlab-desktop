from pathlib import Path

from support.project_tree import talker_tree

from core.project_layout.infer_layout import InferLayout
from core.project_layout.project_layout_file import (
    LoadProjectLayout,
    SaveProjectLayout,
)
from core.project_layout.resolve_recordings import ResolveRecordings
from core.project_layout.scan_project_tree import ScanProjectTree
from phonlab_project.layout.infer_layout import infer_layout
from phonlab_project.layout.project_layout import FolderLevel, ProjectLayout
from phonlab_project.layout.project_layout_file import load_layout, save_layout
from phonlab_project.layout.resolve_recordings import resolve_recordings
from phonlab_project.layout.scan_project_tree import scan_project_tree

# The use cases of the app only call the functions of phonlab_project, which have the
# tests of what they do (test/phonlab_project/layout)


def test_the_use_cases_give_what_the_functions_give(tmp_path: Path):
    talker_tree(tmp_path, annotated=2)

    scan = ScanProjectTree()(str(tmp_path))
    assert scan == scan_project_tree(str(tmp_path))

    suggestion = InferLayout()(scan)
    assert suggestion == infer_layout(scan)

    layout = suggestion.layout
    assert ResolveRecordings()(scan, layout) == resolve_recordings(scan, layout)


def test_a_layout_is_saved_and_loaded_through_the_use_cases(tmp_path: Path):
    layout = ProjectLayout(levels=(FolderLevel(1, "talker"),))

    SaveProjectLayout()(str(tmp_path), layout)

    assert LoadProjectLayout()(str(tmp_path)) == layout
    assert load_layout(str(tmp_path)) == layout
    save_layout(str(tmp_path), ProjectLayout())
    assert LoadProjectLayout()(str(tmp_path)) == ProjectLayout()
