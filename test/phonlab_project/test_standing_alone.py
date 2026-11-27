"""phonlab_project is meant to move into the phonlab library, where there is no desktop
app, so it must not import any of the app's modules (`core`, `res`, `ui`, `data`,
`bootstrap`), nor Qt or SQLAlchemy."""

import json
import subprocess
import sys
from pathlib import Path

APP_PACKAGES = ("core", "res", "ui", "data", "bootstrap", "PyQt6", "sqlalchemy")


def modules_of_the_app_imported() -> list[str]:
    """The modules of the app that loading every part of phonlab_project imports,
    found in a fresh interpreter so that nothing else has imported them"""
    source = Path(__file__).parents[2] / "src"
    code = (
        f"import sys, json; sys.path.insert(0, {str(source)!r}); "
        "import phonlab_project as p; [getattr(p, n) for n in p.__all__]; "
        f"top = {APP_PACKAGES!r}; "
        "print(json.dumps(sorted(n for n in sys.modules if n.split('.')[0] in top)))"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def test_the_package_needs_nothing_of_the_desktop_app():
    assert modules_of_the_app_imported() == []
