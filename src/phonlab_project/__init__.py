"""Read the project database (`phonlab.db`) that phonlab_desktop makes, read a single
annotation file, and make a project database from the files of a folder, from a script
or a notebook.

Reading a project database
    `open_project`, `Project`, `Column`

Reading an annotation file
    `read_annotation`, `read_tiers`

Making and updating a project database from files
    `describe_project`, `import_project`, `add_recordings`, `update_annotations`,
    `import_talkers`, `import_words`, and what they return: `ProjectPlan`,
    `ImportResult`, `TableImportResult`, `Recording`

How a project folder is organized (the contents of `phonlab.toml`)
    `ProjectLayout`, `FolderLevel`, `DataFileRole`, `DataFileKind`, `ChannelRole`,
    `TableFormat`, `ColumnRole`, `TimeUnit`, `load_layout`, `save_layout`

Errors
    `ProjectError`, `ImportNeedsReview`
"""

from phonlab_project.errors import ProjectError
from phonlab_project.importer import (
    ImportNeedsReview,
    ImportResult,
    add_recordings,
    describe_project,
    import_project,
    update_annotations,
)
from phonlab_project.layout.project_layout import (
    ChannelRole,
    DataFileKind,
    DataFileRole,
    FolderLevel,
    ProjectLayout,
)
from phonlab_project.layout.project_layout_file import load_layout, save_layout
from phonlab_project.layout.project_plan import ProjectPlan
from phonlab_project.project import Column, Project, open_project
from phonlab_project.readers.read_annotation import read_annotation
from phonlab_project.readers.read_tiers import read_tiers
from phonlab_project.readers.table_format import ColumnRole, TableFormat, TimeUnit
from phonlab_project.recording import Recording
from phonlab_project.tables import TableImportResult, import_talkers, import_words

__all__ = [
    "ChannelRole",
    "Column",
    "ColumnRole",
    "DataFileKind",
    "DataFileRole",
    "FolderLevel",
    "ImportNeedsReview",
    "ImportResult",
    "Project",
    "ProjectError",
    "ProjectLayout",
    "ProjectPlan",
    "Recording",
    "TableFormat",
    "TableImportResult",
    "TimeUnit",
    "add_recordings",
    "describe_project",
    "import_project",
    "import_talkers",
    "import_words",
    "load_layout",
    "open_project",
    "read_annotation",
    "read_tiers",
    "save_layout",
    "update_annotations",
]
