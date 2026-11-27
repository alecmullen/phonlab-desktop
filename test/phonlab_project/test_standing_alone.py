"""A countdown to phonlab_project standing alone.

The package is meant to move into the phonlab library, where there is no desktop app.
Today it imports modules of the app (`core`, `res`, `ui`) that it needs, which would not
be there. This test lists them, by what has to happen to each before the move. It fails
when the package starts importing a module that is not listed, and when a listed module
is no longer imported (delete it from the list: that is progress). When the lists are
empty, remove the `xfail` from the last test."""

import functools
import json
import subprocess
import sys
from pathlib import Path

import pytest

APP_PACKAGES = ("core", "res", "ui", "data", "bootstrap", "PyQt6", "sqlalchemy")

STILL_FROM_THE_APP = {
    # Belong in the library: the readers, the scan and layout of a project, and the
    # data classes they pass around. They move as they are.
    "move to phonlab": {
        "core.annotation.entity.metadata",
        "core.annotation.entity.recording",
        "core.import_metadata.entity.metadata_table",
        "core.import_metadata.read_metadata_csv",
        "core.project.entity.project_file",
        "core.project.entity.project_plan",
        "core.project_layout.annotation_sources",
        "core.project_layout.channels",
        "core.project_layout.duplicate_audio",
        "core.project_layout.entity.import_report",
        "core.project_layout.entity.project_layout",
        "core.project_layout.entity.project_scan",
        "core.project_layout.filename_template",
        "core.project_layout.pairing",
        "core.read_tiers.annotation_table",
        "core.read_tiers.entity.table_format",
        "core.read_tiers.read_buckeye",
        "core.read_tiers.read_elan",
        "core.read_tiers.read_elan_info",
        "core.read_tiers.read_srt",
        "core.read_tiers.read_tier_table",
        "core.read_tiers.read_tiers",
        "core.read_tiers.read_timit",
        "core.read_tiers.sibling_file",
    },
    # Written as use-case classes of the app (UseCaseSync); they become plain functions
    # in the library, and the app keeps thin use cases that call them.
    "make plain functions, then move": {
        "core.project.scan_project_files",
        "core.project_layout.infer_layout",
        "core.project_layout.project_layout_file",
        "core.project_layout.resolve_recordings",
        "core.project_layout.scan_project_tree",
        "core.base.use_case_sync",
    },
    # Small pure functions that sit in modules of the app: node sharing (add_node_time,
    # get_matching_node, to_label) and the naming and typing of added columns. They move
    # into the library's writer and tables modules, and the app imports them from there.
    "pull out of app modules": {
        "core.annotation.entity.annotation",
        "core.import_metadata.import_metadata",
        "core.parse_textgrid.parse_textgrid",
    },
    # Come in only through the modules above (the repository interface, a use-case base
    # class, a table viewer's data class); they drop out when those are cut loose.
    "drop out by themselves": {
        "core.annotation.entity.tier_label",
        "core.annotation.repository.annotation_repository",
        "core.base.use_case",
        "core.inspect_database.entity.table_data",
    },
    # Constants of the whole app. The ones the readers and layout use need a module of
    # their own, and res.constants must stop importing a state class from the interface.
    "split the constants": {
        "res.constants",
        "ui.base.state",
        "ui.document.state.plot_layout_state",
    },
}


@functools.cache
def app_modules_imported() -> frozenset[str]:
    """The modules of the app (not packages) that `import phonlab_project` loads, found
    in a fresh interpreter so that nothing else has imported them"""
    source = Path(__file__).parents[2] / "src"
    code = (
        f"import sys, json; sys.path.insert(0, {str(source)!r}); import phonlab_project; "
        f"top = {APP_PACKAGES!r}; "
        "print(json.dumps(sorted(n for n, m in sys.modules.items() "
        "if n.split('.')[0] in top and not hasattr(m, '__path__'))))"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, check=True
    )
    return frozenset(json.loads(result.stdout))


def test_the_modules_of_the_app_the_package_needs_are_the_ones_listed():
    listed = {module for group in STILL_FROM_THE_APP.values() for module in group}
    imported = app_modules_imported()

    new = sorted(imported - listed)
    gone = sorted(listed - imported)

    assert not new, (
        f"phonlab_project now needs modules of the app, which it must not: {new}"
    )
    assert not gone, f"no longer needed, delete them from the list: {gone}"


@pytest.mark.xfail(strict=True, reason="still imports modules of the app; see the list")
def test_the_package_stands_alone():
    assert app_modules_imported() == frozenset()
