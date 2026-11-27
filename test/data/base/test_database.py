import sqlite3
from pathlib import Path

import data.annotation.datasource.annotation_datasource  # noqa: F401 - the tables
from data.base.database import SQLiteDatabase
from phonlab_project.schema import SCHEMA_VERSION


def stored_version(directory: Path) -> int:
    connection = sqlite3.connect(directory / "phonlab.db")
    try:
        return connection.execute("PRAGMA user_version").fetchone()[0]
    finally:
        connection.close()


def set_version(directory: Path, version: int) -> None:
    connection = sqlite3.connect(directory / "phonlab.db")
    connection.execute(f"PRAGMA user_version = {version}")
    connection.close()


def test_a_new_database_is_marked_with_the_schema_version(tmp_path: Path):
    database = SQLiteDatabase()
    database.connect(str(tmp_path))
    database.close()

    assert stored_version(tmp_path) == SCHEMA_VERSION


def test_a_database_made_before_versions_were_kept_is_marked_when_opened(
    tmp_path: Path,
):
    database = SQLiteDatabase()
    database.connect(str(tmp_path))
    database.close()
    set_version(tmp_path, 0)

    database.connect(str(tmp_path))
    database.close()

    assert stored_version(tmp_path) == SCHEMA_VERSION


def test_a_version_the_database_already_has_is_left_alone(tmp_path: Path):
    database = SQLiteDatabase()
    database.connect(str(tmp_path))
    database.close()
    set_version(tmp_path, SCHEMA_VERSION + 1)

    database.connect(str(tmp_path))
    database.close()

    assert stored_version(tmp_path) == SCHEMA_VERSION + 1


def test_a_reset_database_is_marked_too(tmp_path: Path):
    database = SQLiteDatabase()
    database.connect(str(tmp_path))
    database.reset()
    database.close()

    assert stored_version(tmp_path) == SCHEMA_VERSION
