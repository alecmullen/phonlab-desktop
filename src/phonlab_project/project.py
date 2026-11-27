import json
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Literal

import numpy as np
import pandas as pd

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
    name: str
    type: str
    kind: ColumnKind


def open_project(path: str | Path) -> "Project":
    """Open the database of a project, read only. `path` is the project folder or the
    `phonlab.db` file in it."""
    file = Path(path)
    if file.is_dir():
        file = file / DATABASE_FILENAME
    if not file.is_file():
        raise ProjectError(f"There is no project database at {file}")
    return Project(file)


class Project:
    """What a project database has, as DataFrames. The database is opened read only,
    so it is safe to use while the app has it open. `schema_version` is the version of
    the schema it was made with; a database made by a newer phonlab is refused."""

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
        self.connection.close()

    def __enter__(self) -> "Project":  # noqa: PYI034 - Self needs Python 3.11
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
        """The names of the tables of the database"""
        rows = self.connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [row[0] for row in rows]

    def has_table(self, table: str) -> bool:
        return table in self.tables()

    def columns(self, table: str) -> pd.DataFrame:
        """The columns of a table with their declared type and whether each is `core`
        (promised), `optional` (made by the app when a project has a value for it) or
        `added` (by the researcher)"""
        return pd.DataFrame(
            [
                {"name": c.name, "type": c.type, "kind": c.kind}
                for c in self._columns(table)
            ],
            columns=["name", "type", "kind"],
        )

    def has_column(self, table: str, column: str) -> bool:
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

    # -- recordings and talkers --

    def recordings(self, fields: bool = True) -> pd.DataFrame:
        """One row per recording, with every column of the table, the optional and
        added ones too. With `fields`, the variables taken from folder and file names
        are columns of their own (`dialect`); one named like a column the table has is
        called `<name>_field`."""
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
        """One row per talker, with every column of the table, the added ones too"""
        return self._read("SELECT * FROM talker ORDER BY id")

    def recording_talkers(self) -> pd.DataFrame:
        """Who is in which recording: `recording` and `talker`, in the order they
        were recorded"""
        return self._read(
            "SELECT r.file_stem AS recording, k.name AS talker "
            "FROM recording_talker AS rt "
            "JOIN recording AS r ON r.id = rt.recording_id "
            "JOIN talker AS k ON k.id = rt.talker_id ORDER BY rt.id"
        )

    # -- tiers and labels --

    def tiers(self) -> pd.DataFrame:
        """One row per tier of each recording: `recording`, `tier`, the `talker` the
        tier was made by (empty unless the source file said) and `n_labels`"""
        return self._read(
            f"SELECT r.file_stem AS recording, t.name AS tier, {self._tier_talker()} "
            "AS talker, COUNT(l.id) AS n_labels FROM annotation_type AS t "
            "JOIN recording AS r ON r.id = t.annotation_id "
            f"{self._tier_talker_join()} "
            "LEFT JOIN annotation_label AS l ON l.annotation_type_id = t.id "
            "GROUP BY t.id ORDER BY r.id, t.id"
        )

    def tier_names(self) -> list[str]:
        """The distinct names of the tiers, in the order they first appear"""
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
        """The labels of the project, one row each: `recording`, `tier`, `talker`
        (that of the tier, empty unless the source file said), `t1` and `t2`
        (seconds) and `label`. Limited to the tiers, talkers and recordings named."""
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
        """The labels of the tier `outer` with `n_<inner>`, how many labels of the tier
        `inner` of the same recording lie within each: from its start to its end.
        (`count_within("word", "phone")` is the number of phones of each word.)"""
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
        """The labels of a tier joined with the project's word table, which says
        what the researcher knows about each word (`freq`, `pos`...): the columns of
        `labels()` and then the table's, empty for a word the table lacks. With
        `count`, also `n_<count>`: how many labels of that tier each one has within
        it (`words(count="phone")` gives `n_phone`)."""
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
