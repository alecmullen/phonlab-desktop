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
        "core.base.use_case_sync",
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
        f"import sys, json; sys.path.insert(0, {str(source)!r}); import phonlab_project as p; [getattr(p, n) for n in p.__all__]; "
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
