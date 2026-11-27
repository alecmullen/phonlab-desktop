"""Read, and make, the project database (`phonlab.db`) that phonlab_desktop uses, from a
script or a notebook.

Reading (`open_project`) uses only sqlite3, numpy and pandas and opens the file read
only. Making and updating it (`import_project` and the functions beside it) reads the
files of a project folder with the readers and layout code in this package."""

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
from phonlab_project.tables import TableImportResult, import_talkers, import_words

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
