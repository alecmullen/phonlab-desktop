"""Make a project database from the files of a project folder, and bring it up to date
as the folder gains recordings and annotation files.

The folder is read as its layout says (see `describe_project`). The layout is the one
given, else the one in the folder's `phonlab.toml`, else one inferred from the files; an
inferred layout is saved to `phonlab.toml` when the database is made, so the project is
read the same way afterwards."""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from core.project.entity.project_file import ProjectFile
from core.project.entity.project_plan import ProjectPlan
from core.project.scan_project_files import plan_project
from core.project_layout.entity.project_layout import ProjectLayout
from core.project_layout.project_layout_file import SaveProjectLayout
from core.read_tiers.read_tier_table import read_tier_table
from core.read_tiers.read_tiers import read_tiers
from phonlab_project.errors import ProjectError
from phonlab_project.schema import writing
from phonlab_project.writer import (
    clear_annotation,
    has_annotation,
    recording_ids,
    upsert_recordings,
    write_annotation,
)


class ImportNeedsReview(ProjectError):
    """The project has things its layout does not account for, or its layout was
    guessed and the guess is not clear, so nothing was imported. `plan` is what was
    found, and `str(plan)` describes it; fix the layout (a `phonlab.toml` in the folder,
    or the `layout` argument) or import anyway with `strict=False`."""

    def __init__(self, plan: ProjectPlan):
        self.plan = plan
        listed = "\n".join(f"  - {problem}" for problem in plan.problems)
        super().__init__(f"The project needs a look before it is imported:\n{listed}")


@dataclass(frozen=True)
class ImportResult:
    """What an import did. Recordings are named by file stem."""

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
    """What reading the project folder finds, with nothing written: its recordings,
    the layout used and where it came from (given, saved in `phonlab.toml`, or
    inferred), and `problems`, what a person should look at first. `str()` of the
    result describes it."""
    return plan_project(str(_folder(path)), layout)


def import_project(
    path: str | Path, layout: ProjectLayout | None = None, strict: bool = True
) -> ImportResult:
    """Make the project database of a folder (`phonlab.db`), or bring the one it has up
    to date: every recording of the folder is added or updated, recordings that left it
    and have no annotation are removed, and the annotation file of each recording whose
    annotation is empty is read. An annotation the database already has is never
    replaced, so corrections made in it are kept (see `update_annotations`).

    With `strict` (the default) a project whose plan has problems is not imported and
    `ImportNeedsReview` is raised; otherwise it is imported as the layout reads it. A
    layout that was given or inferred is saved to the folder's `phonlab.toml`."""
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
        SaveProjectLayout()(str(folder), layout or plan.layout)
    return ImportResult(
        created, updated, removed, result.read, result.kept, result.failed, plan
    )


def add_recordings(
    path: str | Path, layout: ProjectLayout | None = None
) -> ImportResult:
    """Add the recordings the folder has and the database lacks, with their annotations.
    Recordings the database has are not touched."""
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
    """Read the annotation files of recordings the database has. A recording whose
    annotation is empty (it had no file before) is filled in. One that has an
    annotation is left as it is, as the database holds corrections, unless `overwrite`,
    which replaces it with what the file says now. `recordings` limits this to some
    recordings (file stems); a stem the database lacks raises ProjectError."""
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
    return tiers + [
        read_tier_table(tier.path, name, file.audio_path, tier.table)
        for name, tier in file.tier_files.items()
    ]
