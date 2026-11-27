import json
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Literal, Self

import numpy as np
import pandas as pd

from phonlab_project.corpus import CorpusInfo, load_corpus
from phonlab_project.errors import ProjectError
from phonlab_project.schema import (
    DATABASE_FILENAME,
    RECORDING_OPTIONAL_COLUMNS,
    check_version,
)

# Columns the schema promises, and those the app adds only when a project has a value
# for them (see docs/database-schema.md); any other column of a table was added by the
# researcher
CORE_COLUMNS = {
    "recording": (
        "id",
        "file_stem",
        "audio_file",
        "annotation_file",
        "data_files",
        "fields",
    ),
    "talker": ("id", "name"),
    "recording_talker": ("id", "recording_id", "talker_id"),
    "annotation_type": ("id", "annotation_id", "name"),
    "annotation_node": ("id", "annotation_id", "time"),
    "annotation_label": (
        "id",
        "annotation_type_id",
        "label_text",
        "start_node_id",
        "end_node_id",
    ),
    "word": ("id", "word"),
    "recording_channel": ("id", "recording_id", "channel", "audio_file", "talker_id"),
}
OPTIONAL_COLUMNS = {
    "recording": tuple(RECORDING_OPTIONAL_COLUMNS),
    "annotation_type": ("talker_id",),
}
# the times of two labels are the same when they are this close (seconds)
TIME_TOLERANCE = 1e-9

ColumnKind = Literal["core", "optional", "added"]


@dataclass(frozen=True)
class Column:
    """A column of a table of the project database.

    Attributes
    ----------

    name : str
        The name of the column.

    type : str
        The type the database declares for it (`TEXT`, `INTEGER`, `REAL`...).

    kind : {"core", "optional", "added"}
        `core` columns are always there. `optional` ones are made only when a project
        has a value for them (a project without video has no `video_file`). `added`
        ones are the researcher's (the `age` of a talker, the `pos` of a word)."""

    name: str
    type: str
    kind: ColumnKind


def open_project(path: str | Path) -> "Project":
    """Open the database of a project for reading.

    The database is opened read only, so this is safe to do while the desktop app has
    the project open.

    Parameters
    ----------

    path : path-like
        The project folder, or the `phonlab.db` file in it.

    Returns
    -------

    project : Project
        Use it as a context manager (`with open_project(...) as project:`) to have the
        database closed when you are done, or call `Project.close()`.

    Raises
    ------

    ProjectError
        If there is no database at `path`, the file is not a project database, or it
        was made by a newer version of phonlab than this one.

    Examples
    --------

    >>> with open_project("my_corpus") as project:  # doctest: +SKIP
    ...     words = project.words(count="phone")
    ...     words.groupby("n_phone").t2.count()"""
    file = Path(path)
    if file.is_dir():
        file = file / DATABASE_FILENAME
    if not file.is_file():
        raise ProjectError(f"There is no project database at {file}")
    return Project(file)


class Project:
    """The project database (`phonlab.db`) of a project, as DataFrames.

    Made by `open_project`. The database is opened read only. A `Project` is a context
    manager that closes the database when its block ends.

    Attributes
    ----------

    file : pathlib.Path
        The database file.

    connection : sqlite3.Connection
        The read-only connection, for queries of your own.

    schema_version : int
        The version of the schema the database was made with.

    Examples
    --------

    >>> with open_project("my_corpus") as project:  # doctest: +SKIP
    ...     project.tiers()
    ...     project.labels(tier="word", talker="Ann")"""

    schema_version: int

    def __init__(self, file: Path):
        self.file = file
        self.connection = sqlite3.connect(
            f"{file.resolve().as_uri()}?mode=ro", uri=True
        )
        try:
            names = self.tables()
        except sqlite3.DatabaseError as error:
            self.connection.close()
            raise ProjectError(f"{file} is not a project database: {error}") from error
        if "recording" not in names or "annotation_label" not in names:
            self.connection.close()
            raise ProjectError(
                f"{file} is not a project database: it has no recordings"
            )
        try:
            self.schema_version = check_version(self.connection, file)
        except ProjectError:
            self.connection.close()
            raise

    def close(self) -> None:
        """Close the database."""
        self.connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    # -- what the project has --

    def tables(self) -> list[str]:
        """The names of the tables of the database.

        Returns
        -------

        tables : list of str"""
        rows = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [row[0] for row in rows]

    def has_table(self, table: str) -> bool:
        """Whether the database has a table.

        Parameters
        ----------

        table : str

        Returns
        -------

        has : bool"""
        return table in self.tables()

    def columns(self, table: str) -> pd.DataFrame:
        """The columns of a table, and whether each is one every project has or one added.

        Parameters
        ----------

        table : str
            A name from `tables()`.

        Returns
        -------

        columns : pandas.DataFrame
            One row per column: `name`, `type` and `kind` (see `Column`).

        Raises
        ------

        ProjectError
            If the project has no such table."""
        return pd.DataFrame(
            [
                {"name": c.name, "type": c.type, "kind": c.kind}
                for c in self._columns(table)
            ],
            columns=["name", "type", "kind"],
        )

    def has_column(self, table: str, column: str) -> bool:
        """Whether a table has a column; false if there is no such table.

        Use it before using a column that only some projects have (`pos` in the word table,
        `age` in the talker table).

        Parameters
        ----------

        table : str

        column : str

        Returns
        -------

        has : bool"""
        return self.has_table(table) and any(
            c.name == column for c in self._columns(table)
        )

    def _columns(self, table: str) -> list[Column]:
        if not self.has_table(table):
            raise ProjectError(
                f"The project has no table called {table!r}; it has {self.tables()}"
            )
        core = CORE_COLUMNS.get(table, ())
        optional = OPTIONAL_COLUMNS.get(table, ())
        return [
            Column(
                row[1],
                row[2],
                "core"
                if row[1] in core
                else "optional"
                if row[1] in optional
                else "added",
            )
            for row in self.connection.execute(f'PRAGMA table_info("{table}")')
        ]

    def corpus(self) -> CorpusInfo:
        """What the project says about the corpus as a whole.

        Returns
        -------

        info : dict
            The `[corpus]` section of the project's `phonlab.toml`: `title`, `creator`
            (a list when there are several), `doi`... whatever the project gives. Empty
            if there is none."""
        return load_corpus(self.file.parent)

    # -- recordings and talkers --

    def recordings(self, fields: bool = True) -> pd.DataFrame:
        """The recordings of the project.

        Parameters
        ----------

        fields : bool (default True)
            Make the variables taken from folder and file names (`dialect`, `session`...)
            columns of their own. One named like a column the table has is called
            `<name>_field`. If False the table's `fields` column holds them as JSON text.

        Returns
        -------

        recordings : pandas.DataFrame
            One row per recording with every column of the table: `file_stem`, `audio_file`,
            `annotation_file`, `data_files`, and the optional (`video_file`, `media_offset`,
            `target_talker`) and added ones the project has."""
        table = self._read("SELECT * FROM recording ORDER BY id")
        table["data_files"] = table["data_files"].map(_from_json)
        parsed = table["fields"].map(_from_json)
        table = table.drop(columns="fields")
        if not fields:
            table["fields"] = parsed
            return table
        names = list(dict.fromkeys(name for row in parsed for name in row))
        for name in names:
            column = f"{name}_field" if name in table.columns else name
            table[column] = [row.get(name) for row in parsed]
        return table

    def talkers(self) -> pd.DataFrame:
        """The talkers of the project.

        Returns
        -------

        talkers : pandas.DataFrame
            One row per talker: `id`, `name` and any columns added from a table of talker
            information (`age`, `sex`...)."""
        return self._read("SELECT * FROM talker ORDER BY id")

    def recording_talkers(self) -> pd.DataFrame:
        """Who is in which recording.

        Returns
        -------

        recording_talkers : pandas.DataFrame
            `recording` (the file stem) and `talker`, one row for each talker of each
            recording, in the order they were recorded."""
        return self._read(
            "SELECT r.file_stem AS recording, k.name AS talker "
            "FROM recording_talker AS rt "
            "JOIN recording AS r ON r.id = rt.recording_id "
            "JOIN talker AS k ON k.id = rt.talker_id ORDER BY rt.id"
        )

    # -- tiers and labels --

    def tiers(self) -> pd.DataFrame:
        """The tiers of the annotations of every recording.

        Returns
        -------

        tiers : pandas.DataFrame
            One row per tier of each recording: `recording`, `tier`, `talker` (who made the
            tier, where the source file said; empty otherwise) and `n_labels`."""
        return self._read(
            f"SELECT r.file_stem AS recording, t.name AS tier, {self._tier_talker()} "
            "AS talker, COUNT(l.id) AS n_labels FROM annotation_type AS t "
            "JOIN recording AS r ON r.id = t.annotation_id "
            f"{self._tier_talker_join()} "
            "LEFT JOIN annotation_label AS l ON l.annotation_type_id = t.id "
            "GROUP BY t.id ORDER BY r.id, t.id"
        )

    def tier_names(self) -> list[str]:
        """The distinct names of the tiers, in the order they first appear.

        Returns
        -------

        names : list of str"""
        rows = self.connection.execute(
            "SELECT name FROM annotation_type GROUP BY name ORDER BY MIN(id)"
        )
        return [row[0] for row in rows]

    def labels(
        self,
        tier: str | Sequence[str] | None = None,
        talker: str | Sequence[str] | None = None,
        recording: str | Sequence[str] | None = None,
    ) -> pd.DataFrame:
        """The labels of the annotations, one row each.

        Parameters
        ----------

        tier : str or sequence of str, optional
            Only the labels of these tiers.

        talker : str or sequence of str, optional
            Only the labels of tiers made by these talkers.

        recording : str or sequence of str, optional
            Only the labels of these recordings (file stems).

        Returns
        -------

        labels : pandas.DataFrame
            `recording`, `tier`, `talker`, `t1` and `t2` (start and end, seconds) and
            `label`.

        Raises
        ------

        ProjectError
            If a tier, talker or recording named is not in the project (the message lists
            what is), or a talker is asked for and no tier of the project has one."""
        conditions, parameters = [], []
        for column, wanted in (
            ("t.name", self._known_tiers(tier)),
            ("r.file_stem", self._known_recordings(recording)),
            (self._tier_talker(), self._known_talkers(talker)),
        ):
            if wanted is not None:
                marks = ", ".join("?" * len(wanted))
                conditions.append(f"{column} IN ({marks})")
                parameters.extend(wanted)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return self._read(
            "SELECT r.file_stem AS recording, t.name AS tier, "
            f"{self._tier_talker()} AS talker, s.time AS t1, e.time AS t2, "
            "l.label_text AS label FROM annotation_label AS l "
            "JOIN annotation_type AS t ON t.id = l.annotation_type_id "
            "JOIN recording AS r ON r.id = t.annotation_id "
            "JOIN annotation_node AS s ON s.id = l.start_node_id "
            "JOIN annotation_node AS e ON e.id = l.end_node_id "
            f"{self._tier_talker_join()} {where} "
            "ORDER BY r.id, t.id, s.time, e.time",
            parameters,
        )

    def count_within(self, outer: str, inner: str) -> pd.DataFrame:
        """The labels of one tier with how many labels of another lie within each.

        `count_within("word", "phone")` gives the number of phones of each word. A label of
        `inner` is within one of `outer` of the same recording if it begins and ends inside
        it.

        Parameters
        ----------

        outer : str
            The tier whose labels are returned.

        inner : str
            The tier to count.

        Returns
        -------

        labels : pandas.DataFrame
            The labels of `outer`, as `labels()` gives them, and the column `n_<inner>`.

        Raises
        ------

        ProjectError
            If either tier is not in the project."""
        outer_labels = self.labels(tier=outer)
        inner_labels = self.labels(tier=inner)
        counts = pd.Series(0, index=outer_labels.index, dtype="int64")
        for name, group in outer_labels.groupby("recording", sort=False):
            inside = inner_labels[inner_labels.recording == name].sort_values("t1")
            starts = inside.t1.to_numpy()
            ends = inside.t2.to_numpy()
            first = np.searchsorted(
                starts, group.t1.to_numpy() - TIME_TOLERANCE, "left"
            )
            last = np.searchsorted(
                starts, group.t2.to_numpy() + TIME_TOLERANCE, "right"
            )
            counts[group.index] = [
                int(np.count_nonzero(ends[a:b] <= end + TIME_TOLERANCE))
                for a, b, end in zip(first, last, group.t2, strict=True)
            ]
        return outer_labels.assign(**{f"n_{inner}": counts})

    # -- words --

    def words(self, tier: str = "word", count: str | None = None) -> pd.DataFrame:
        """The labels of a tier joined with the project's word table.

        The word table (made with `import_words`) says what the researcher knows about each
        word, such as its frequency and part of speech.

        Parameters
        ----------

        tier : str (default "word")
            The tier of words.

        count : str, optional
            A tier whose labels to count within each word (`count="phone"` adds `n_phone`).

        Returns
        -------

        words : pandas.DataFrame
            The columns `labels()` gives, then those of the word table (`freq`, `pos`...),
            empty for a word the table lacks. Words are matched as written, so case counts.

        Raises
        ------

        ProjectError
            If the project has no word table, or no such tier.

        Examples
        --------

        >>> words = project.words(count="phone")  # doctest: +SKIP
        >>> words["duration"] = words.t2 - words.t1  # doctest: +SKIP
        >>> words.groupby(["n_phone", "pos"]).duration.mean()  # doctest: +SKIP"""
        if not self.has_table("word"):
            raise ProjectError(
                "The project has no word table; add one in the app with "
                "Project > Add New Files… > words"
            )
        labels = (
            self.labels(tier=tier) if count is None else self.count_within(tier, count)
        )
        table = self._read("SELECT * FROM word ORDER BY id").drop(columns="id")
        return labels.merge(
            table, how="left", left_on="label", right_on="word", suffixes=("", "_word")
        ).drop(columns="word")

    # -- helpers --

    def _read(self, query: str, parameters: Sequence[object] = ()) -> pd.DataFrame:
        return pd.read_sql(query, self.connection, params=tuple(parameters))

    def _tier_talker(self) -> str:
        return "k.name" if self.has_column("annotation_type", "talker_id") else "NULL"

    def _tier_talker_join(self) -> str:
        if self.has_column("annotation_type", "talker_id"):
            return "LEFT JOIN talker AS k ON k.id = t.talker_id"
        return ""

    def _known_tiers(self, tier: str | Sequence[str] | None) -> list[str] | None:
        return self._known(tier, self.tier_names(), "tier")

    def _known_recordings(
        self, recording: str | Sequence[str] | None
    ) -> list[str] | None:
        stems = [
            r[0] for r in self.connection.execute("SELECT file_stem FROM recording")
        ]
        return self._known(recording, stems, "recording")

    def _known_talkers(self, talker: str | Sequence[str] | None) -> list[str] | None:
        if talker is None:
            return None
        if not self.has_column("annotation_type", "talker_id"):
            raise ProjectError(
                "No tier of this project says who made it, so labels cannot be "
                "limited to a talker"
            )
        names = [r[0] for r in self.connection.execute("SELECT name FROM talker")]
        return self._known(talker, names, "talker")

    @staticmethod
    def _known(
        wanted: str | Sequence[str] | None, available: list[str], what: str
    ) -> list[str] | None:
        if wanted is None:
            return None
        names = [wanted] if isinstance(wanted, str) else list(wanted)
        missing = [name for name in names if name not in available]
        if missing:
            raise ProjectError(
                f"The project has no {what} {missing}; it has {available}"
            )
        return names


def _from_json(value: str | None) -> dict:
    return json.loads(value) if value else {}
