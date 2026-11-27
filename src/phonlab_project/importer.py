"""Make a project database from the files of a project folder, and bring it up to date
as the folder gains recordings and annotation files.

The folder is read as its layout says (see `describe_project`). The layout is the one
given, else the one in the folder's `phonlab.toml`, else one inferred from the files; an
inferred layout is saved to `phonlab.toml` when the database is made, so the project is
read the same way afterwards."""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from phonlab_project.errors import ProjectError
from phonlab_project.layout.plan_project import plan_project
from phonlab_project.layout.project_file import ProjectFile
from phonlab_project.layout.project_layout import ProjectLayout
from phonlab_project.layout.project_layout_file import save_layout
from phonlab_project.layout.project_plan import ProjectPlan
from phonlab_project.readers.read_tier_table import read_tier_table
from phonlab_project.readers.read_tiers import read_tiers, with_tier_talkers
from phonlab_project.schema import writing
from phonlab_project.writer import (
    clear_annotation,
    has_annotation,
    recording_ids,
    upsert_recordings,
    write_annotation,
)


class ImportNeedsReview(ProjectError):
    """Raised by `import_project` when the project needs a look before it is imported.

    The project has things its layout does not account for, or its layout was guessed
    and the guess is not clear, and nothing was imported. It is a `ProjectError`.

    Attributes
    ----------

    plan : ProjectPlan
        What was found. `str(plan)` describes it and `plan.problems` lists what needs
        a look. Fix the layout (a `phonlab.toml` in the folder, or the `layout` argument)
        or import anyway with `strict=False`."""

    def __init__(self, plan: ProjectPlan):
        self.plan = plan
        listed = "\n".join(f"  - {problem}" for problem in plan.problems)
        super().__init__(f"The project needs a look before it is imported:\n{listed}")


@dataclass(frozen=True)
class ImportResult:
    """What an import did. Recordings are named by their file stem.

    Attributes
    ----------

    created : int
        Recordings added to the database.

    updated : int
        Recordings whose files and talkers were brought up to date.

    removed : int
        Recordings that left the folder and had no annotation, so were removed.

    read : list of str
        Recordings whose annotation file was read.

    kept : list of str
        Recordings that already had an annotation, which was left as it was.

    failed : dict
        Recording -> why its annotation file could not be read. An unreadable file never
        stops the others or damages an annotation the database has.

    plan : ProjectPlan
        What the folder was found to hold."""

    created: int = 0  # recordings added to the database
    updated: int = 0  # recordings whose files and talkers were brought up to date
    removed: int = 0  # recordings no longer in the project that had no annotation
    read: list[str] = field(default_factory=list)  # annotations read
    kept: list[str] = field(default_factory=list)  # had an annotation, left as it was
    failed: dict[str, str] = field(default_factory=dict)  # annotation -> why not read
    plan: ProjectPlan | None = None


def describe_project(
    path: str | Path, layout: ProjectLayout | None = None
) -> ProjectPlan:
    """Read a project folder and say what it holds, writing nothing.

    Parameters
    ----------

    path : path-like
        The project folder.

    layout : ProjectLayout, optional
        How the folder is organized. By default the layout saved in the folder's
        `phonlab.toml` is used, and if there is none one is inferred from the files.

    Returns
    -------

    plan : ProjectPlan
        The recordings (`plan.recordings`), the layout and where it came from, and
        `plan.problems`, what a person should look at before importing. `print(plan)`
        describes it.

    Raises
    ------

    ProjectError
        If `path` is not a folder.

    Examples
    --------

    >>> plan = describe_project("my_corpus")  # doctest: +SKIP
    >>> print(plan)  # doctest: +SKIP
    >>> plan.recordings[0].talkers  # doctest: +SKIP"""
    return plan_project(str(_folder(path)), layout)


def import_project(
    path: str | Path, layout: ProjectLayout | None = None, strict: bool = True
) -> ImportResult:
    """Make the project database (`phonlab.db`) of a folder, or bring it up to date.

    Every recording of the folder is added or updated, recordings that left the folder
    and have no annotation are removed, and the annotation file of each recording whose
    annotation is empty is read. An annotation the database already has is never
    replaced, so corrections made in it are kept (see `update_annotations`). A layout that
    was given or inferred is saved to the folder's `phonlab.toml`, so that the folder is
    read the same way next time.

    Parameters
    ----------

    path : path-like
        The project folder.

    layout : ProjectLayout, optional
        How the folder is organized. By default the layout saved in `phonlab.toml` is
        used, and if there is none one is inferred from the files.

    strict : bool (default True)
        Refuse a project whose plan has problems (annotation files that belong to no
        sound file, sound files that look like copies or do not fit the filename
        template, an unclear guess at the layout...): nothing is written and
        `ImportNeedsReview` is raised. If False the project is imported as the layout
        reads it.

    Returns
    -------

    result : ImportResult

    Raises
    ------

    ImportNeedsReview
        If `strict` and the project has problems.

    ProjectError
        If `path` is not a folder, the database is in use by another program (the desktop
        app may have the project open), or it was made by a newer version of phonlab.

    Examples
    --------

    >>> print(describe_project("my_corpus"))  # doctest: +SKIP
    >>> import_project("my_corpus")  # doctest: +SKIP"""
    folder = _folder(path)
    plan = plan_project(str(folder), layout)
    if strict and plan.problems:
        raise ImportNeedsReview(plan)

    with writing(folder, create=True) as connection:
        created, updated, removed = upsert_recordings(
            connection, plan.recordings, remove_others=True
        )
        result = _read_annotations(connection, plan.files, replace=False)
    if plan.layout_source != "saved":
        save_layout(str(folder), layout or plan.layout)
    return ImportResult(
        created, updated, removed, result.read, result.kept, result.failed, plan
    )


def add_recordings(
    path: str | Path, layout: ProjectLayout | None = None
) -> ImportResult:
    """Add the recordings a folder has and the database lacks, with their annotations.

    Recordings the database has are not touched.

    Parameters
    ----------

    path : path-like
        The project folder, which must have a project database.

    layout : ProjectLayout, optional
        As for `import_project`.

    Returns
    -------

    result : ImportResult

    Raises
    ------

    ProjectError
        If the folder has no project database, or as for `import_project`."""
    folder = _folder(path)
    plan = plan_project(str(folder), layout)
    with writing(folder) as connection:
        known = recording_ids(connection)
        new = [file for file in plan.files if file.file_stem not in known]
        created, _, _ = upsert_recordings(
            connection, [f.recording for f in new if f.recording], remove_others=False
        )
        result = _read_annotations(connection, new, replace=False)
    return ImportResult(created, 0, 0, result.read, result.kept, result.failed, plan)


def update_annotations(
    path: str | Path,
    recordings: list[str] | None = None,
    overwrite: bool = False,
    layout: ProjectLayout | None = None,
) -> ImportResult:
    """Read the annotation files of recordings the database has.

    A recording whose annotation is empty (it had no file before) is filled in. One that
    has an annotation is left as it is, because the database is where corrections are
    kept, unless `overwrite`.

    Parameters
    ----------

    path : path-like
        The project folder, which must have a project database.

    recordings : list of str, optional
        Only these recordings (file stems). All of them by default.

    overwrite : bool (default False)
        Replace annotations the database has with what the files say now.

    layout : ProjectLayout, optional
        As for `import_project`.

    Returns
    -------

    result : ImportResult
        `result.read` are the recordings whose annotation was read, `result.kept` those
        left as they were, and `result.failed` the files that could not be read (the
        annotation of such a recording is left as it was).

    Raises
    ------

    ProjectError
        If a recording named is not in the database, or as for `add_recordings`."""
    folder = _folder(path)
    plan = plan_project(str(folder), layout)
    with writing(folder) as connection:
        known = recording_ids(connection)
        wanted = set(recordings) if recordings is not None else set(known)
        if missing := sorted(wanted - known.keys()):
            raise ProjectError(f"The project has no recording {missing}")
        files = [file for file in plan.files if file.file_stem in wanted]
        result = _read_annotations(connection, files, replace=overwrite)
        # what the annotation file says (talkers, its name) is kept with the recording
        upsert_recordings(
            connection,
            [f.recording for f in files if f.recording and f.file_stem in result.read],
            remove_others=False,
        )
    return ImportResult(
        0, len(result.read), 0, result.read, result.kept, result.failed, plan
    )


def _folder(path: str | Path) -> Path:
    folder = Path(path)
    if not folder.is_dir():
        raise ProjectError(f"{folder} is not a folder")
    return folder


def _read_annotations(
    connection: sqlite3.Connection, files: list[ProjectFile], replace: bool
) -> ImportResult:
    """Read the annotation of each file that has one into its recording, which must be
    in the database. A recording that has an annotation is kept as it is unless
    `replace`. A file that cannot be read leaves the recording as it was."""
    ids = recording_ids(connection)
    read: list[str] = []
    kept: list[str] = []
    failed: dict[str, str] = {}
    for file in files:
        if not (file.textgrid_path or file.tier_files):
            continue
        id = ids[file.file_stem]
        if has_annotation(connection, id) and not replace:
            kept.append(file.file_stem)
            continue
        try:
            tiers = _tiers_of(file)
        except Exception as error:  # noqa: BLE001 - readers fail in many ways; one bad file must not stop the rest
            failed[file.file_stem] = str(error) or type(error).__name__
            continue
        clear_annotation(connection, id)
        write_annotation(connection, id, tiers)
        read.append(file.file_stem)
    return ImportResult(read=read, kept=kept, failed=failed)


def _tiers_of(file: ProjectFile) -> list[dict]:
    """The tiers of a recording's annotation: those of its annotation file and a tier for
    each file that holds one"""
    tiers = read_tiers(file.textgrid_path) if file.textgrid_path else []
    if file.recording is not None:
        tiers = with_tier_talkers(tiers, file.recording.tier_talkers)
    return tiers + [
        read_tier_table(tier.path, name, file.audio_path, tier.table)
        for name, tier in file.tier_files.items()
    ]
