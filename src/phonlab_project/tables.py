"""Add what a researcher knows about talkers and words to the project database: a table
(a DataFrame or a CSV file) with a row for each talker or word, whose other columns
become columns of the database. The columns are the researcher's (`age`, `sex`, `pos`,
`freq`...); docs/database-schema.md suggests names for the usual ones."""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from phonlab_project.columns import column_name, convert, infer_sql_type
from phonlab_project.errors import ProjectError
from phonlab_project.metadata import SqlType
from phonlab_project.readers.metadata_table import MetadataTable
from phonlab_project.readers.read_metadata_csv import read_metadata_csv
from phonlab_project.schema import WORD_TABLE, add_column, writing

MAX_LISTED = 50

Table = pd.DataFrame | str | Path
# a column to add: the header it comes from, its name in the database and its type
ColumnPlan = tuple[str, str, SqlType]


@dataclass(frozen=True)
class TableImportResult:
    """What adding a table did. `rows` is how many rows went into the database (talkers
    that got values, words stored) and `columns` the names of the columns added or
    updated (made safe for the database, so they may differ from the table's headers).
    `unmatched_rows` are the rows that name nothing in the project (talkers the project
    lacks; words the tier lacks) and `missing` what the project has that the table
    lacks (talkers; words, most frequent first). Each list shows at most 50, and
    `n_` says how many there are. `duplicates` is how many rows repeat an earlier one."""

    rows: int = 0
    columns: list[str] = field(default_factory=list)
    duplicates: int = 0
    n_unmatched_rows: int = 0
    unmatched_rows: list[str] = field(default_factory=list)
    n_missing: int = 0
    missing: list[str] = field(default_factory=list)


def import_talkers(
    path: str | Path,
    table: Table,
    key: str | None = None,
    columns: list[str] | None = None,
) -> TableImportResult:
    """Add the columns of `table` to the talkers of the project. `key` is the column
    that names the talker (the first by default; case and surrounding spaces do not
    matter), `columns` which of the others to add (all by default). A column the
    database already has is updated; empty cells stay empty. If several rows name a
    talker the last is used."""
    data = _as_table(table)
    key = _key(data, key)
    with writing(path) as connection:
        names = [row[0] for row in connection.execute("SELECT name FROM talker")]
        plans = _plan_columns(data, key, columns, ("id", "name"))
        by_name = {name.casefold(): name for name in names}

        values: dict[str, dict[str, object]] = {}
        unmatched: list[str] = []
        duplicates = 0
        for row in data.rows:
            value = row[data.headers.index(key)].strip()
            name = by_name.get(value.casefold())
            if name is None:
                if value:
                    unmatched.append(value)
                continue
            duplicates += name in values
            values[name] = {
                new: convert(row[data.headers.index(source)], sql_type)
                for source, new, sql_type in plans
            }

        for _, new, sql_type in plans:
            add_column(connection, "talker", new, sql_type.value)
        if plans:
            assignments = ", ".join(f'"{new}" = ?' for _, new, _ in plans)
            connection.executemany(
                f"UPDATE talker SET {assignments} WHERE name = ?",
                [
                    (*(row[new] for _, new, _ in plans), name)
                    for name, row in values.items()
                ],
            )
        missing = sorted(set(names) - values.keys())
    return _result(len(values), plans, duplicates, unmatched, missing)


def import_words(
    path: str | Path,
    table: Table,
    tier: str = "word",
    key: str | None = None,
    columns: list[str] | None = None,
) -> TableImportResult:
    """Make the word table of the project from `table`: `key` is the column that has
    the words (the first by default) and the others become columns of the word table.
    A word table the project already has is replaced. Words are compared with the
    label text of `tier` as written (the case counts), so the result says which words
    of the tier the table lacks. An empty cell stays empty, and a word that several
    rows have is taken from the first."""
    data = _as_table(table)
    key = _key(data, key)
    plans = _plan_columns(data, key, columns, ("id", "word"))
    with writing(path) as connection:
        in_tier = _tier_label_counts(connection, tier)

        rows: dict[str, list[object]] = {}
        duplicates = 0
        for row in data.rows:
            word = row[data.headers.index(key)]
            if word == "":
                continue
            if word in rows:
                duplicates += 1
                continue
            rows[word] = [
                convert(row[data.headers.index(source)], sql_type)
                for source, _, sql_type in plans
            ]

        connection.execute("DROP TABLE IF EXISTS word")
        connection.execute(WORD_TABLE)
        for _, new, sql_type in plans:
            add_column(connection, "word", new, sql_type.value)
        names = ", ".join(['"word"', *(f'"{new}"' for _, new, _ in plans)])
        marks = ", ".join("?" * (len(plans) + 1))
        connection.executemany(
            f"INSERT INTO word ({names}) VALUES ({marks})",
            [(word, *values) for word, values in rows.items()],
        )

    extra = [word for word in rows if word not in in_tier]
    absent = sorted(
        (word for word in in_tier if word not in rows),
        key=lambda word: (-in_tier[word], word),
    )
    return _result(len(rows), plans, duplicates, extra, absent)


def _as_table(table: Table) -> MetadataTable:
    """The table as rows of text, as a CSV file is read"""
    if isinstance(table, pd.DataFrame):
        frame = table.convert_dtypes()  # whole numbers stay whole
        return MetadataTable(
            [str(header) for header in frame.columns],
            [
                ["" if pd.isna(cell) else str(cell).strip() for cell in row]
                for row in frame.itertuples(index=False, name=None)
            ],
        )
    try:
        return read_metadata_csv(str(table))
    except (OSError, ValueError) as error:
        raise ProjectError(f"Cannot read {table} as a table: {error}") from error


def _key(table: MetadataTable, key: str | None) -> str:
    if not table.headers:
        raise ProjectError("The table has no columns")
    if key is None:
        return table.headers[0]
    if key not in table.headers:
        raise ProjectError(f"The table has no column {key!r}; it has {table.headers}")
    return key


def _plan_columns(
    table: MetadataTable, key: str, wanted: list[str] | None, reserved: tuple[str, ...]
) -> list[ColumnPlan]:
    """The columns to add as (header, name in the database, type), with names made safe
    for the database and kept clear of the `reserved` ones the table has itself"""
    if wanted is not None and (
        unknown := [h for h in wanted if h not in table.headers]
    ):
        raise ProjectError(f"The table has no column {unknown}; it has {table.headers}")
    taken = {name.casefold() for name in reserved}
    plans = []
    for header in table.headers:
        if header == key or (wanted is not None and header not in wanted):
            continue
        name = column_name(header, taken)
        taken.add(name.casefold())
        plans.append((header, name, infer_sql_type(table.column(header))))
    return plans


def _tier_label_counts(connection: sqlite3.Connection, tier: str) -> dict[str, int]:
    counts = dict(
        connection.execute(
            "SELECT label_text, COUNT(*) FROM annotation_label "
            "JOIN annotation_type ON annotation_type.id = annotation_type_id "
            "WHERE annotation_type.name = ? GROUP BY label_text",
            (tier,),
        )
    )
    if not counts:
        tiers = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM annotation_type GROUP BY name ORDER BY MIN(id)"
            )
        ]
        raise ProjectError(f"The project has no tier {tier!r}; it has {tiers}")
    return counts


def _result(
    rows: int,
    plans: list[ColumnPlan],
    duplicates: int,
    unmatched: list[str],
    missing: list[str],
) -> TableImportResult:
    return TableImportResult(
        rows,
        [new for _, new, _ in plans],
        duplicates,
        len(unmatched),
        unmatched[:MAX_LISTED],
        len(missing),
        missing[:MAX_LISTED],
    )
