"""Read, and make, the project database (`phonlab.db`) that phonlab_desktop uses, from a
script or a notebook.

Reading (`open_project`) uses only sqlite3, numpy and pandas and opens the file read
only. Making and updating it (`import_project` and the functions beside it) reads the
files of a project folder with the readers and layout code of phonlab.

The names below are loaded when first used, so that importing a part of the package (the
readers, say) does not load the importer, which still needs modules of the desktop app
that themselves import those parts."""

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from phonlab_project.errors import ProjectError
    from phonlab_project.importer import (
        ImportNeedsReview,
        ImportResult,
        add_recordings,
        describe_project,
        import_project,
        update_annotations,
    )
    from phonlab_project.project import Column, Project, open_project
    from phonlab_project.tables import (
        TableImportResult,
        import_talkers,
        import_words,
    )

_MODULES = {
    "Column": "project",
    "ImportNeedsReview": "importer",
    "ImportResult": "importer",
    "Project": "project",
    "ProjectError": "errors",
    "TableImportResult": "tables",
    "add_recordings": "importer",
    "describe_project": "importer",
    "import_project": "importer",
    "import_talkers": "tables",
    "import_words": "tables",
    "open_project": "project",
    "update_annotations": "importer",
}

__all__ = [
    "Column",
    "ImportNeedsReview",
    "ImportResult",
    "Project",
    "ProjectError",
    "TableImportResult",
    "add_recordings",
    "describe_project",
    "import_project",
    "import_talkers",
    "import_words",
    "open_project",
    "update_annotations",
]


def __getattr__(name: str) -> object:
    module = _MODULES.get(name)
    if module is None:
        raise AttributeError(f"module 'phonlab_project' has no attribute {name!r}")
    value = getattr(importlib.import_module(f"phonlab_project.{module}"), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return __all__
