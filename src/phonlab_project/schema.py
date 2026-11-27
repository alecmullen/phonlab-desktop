"""The schema of the project database (`phonlab.db`): its version and the tables a
project starts with. docs/database-schema.md describes what the tables mean."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from phonlab_project.errors import ProjectError

DATABASE_FILENAME = "phonlab.db"

# Stored in the file as SQLite's `PRAGMA user_version`. It goes up when a change to the
# schema would break a script (or the app) that knows the older one. A file that has no
# version (0) but has the project tables was made before versions were kept, and is
# version 1.
SCHEMA_VERSION = 1

# how long (seconds) a write waits for a database another program is writing to
LOCK_TIMEOUT = 2

# Columns of the recording table that are only added when a recording has a value for
# them, as most projects have none: name -> SQL type
RECORDING_OPTIONAL_COLUMNS = {
    "video_file": "TEXT",
    "media_offset": "REAL",
    "target_talker": "TEXT",
}

CORE_TABLES = (
    """CREATE TABLE IF NOT EXISTS recording (
        id INTEGER NOT NULL,
        file_stem VARCHAR(255) NOT NULL,
        audio_file VARCHAR(1024),
        annotation_file VARCHAR(1024),
        data_files JSON,
        fields JSON,
        PRIMARY KEY (id),
        UNIQUE (file_stem)
    )""",
    """CREATE TABLE IF NOT EXISTS talker (
        id INTEGER NOT NULL,
        name VARCHAR(255) NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (name)
    )""",
    """CREATE TABLE IF NOT EXISTS annotation_node (
        id INTEGER NOT NULL,
        annotation_id INTEGER NOT NULL,
        time DOUBLE NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(annotation_id) REFERENCES recording (id)
    )""",
    """CREATE TABLE IF NOT EXISTS annotation_type (
        id INTEGER NOT NULL,
        annotation_id INTEGER NOT NULL,
        name VARCHAR(255) NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(annotation_id) REFERENCES recording (id)
    )""",
    """CREATE TABLE IF NOT EXISTS recording_talker (
        id INTEGER NOT NULL,
        recording_id INTEGER NOT NULL,
        talker_id INTEGER NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (recording_id, talker_id),
        FOREIGN KEY(recording_id) REFERENCES recording (id),
        FOREIGN KEY(talker_id) REFERENCES talker (id)
    )""",
    """CREATE TABLE IF NOT EXISTS annotation_label (
        id INTEGER NOT NULL,
        annotation_type_id INTEGER NOT NULL,
        label_text TEXT NOT NULL,
        start_node_id INTEGER NOT NULL,
        end_node_id INTEGER NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(annotation_type_id) REFERENCES annotation_type (id),
        FOREIGN KEY(start_node_id) REFERENCES annotation_node (id),
        FOREIGN KEY(end_node_id) REFERENCES annotation_node (id)
    )""",
)

# Tables a project has only once it has something to put in them
WORD_TABLE = """CREATE TABLE word (
        id INTEGER NOT NULL,
        word TEXT NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (word)
    )"""
CHANNEL_TABLE = """CREATE TABLE IF NOT EXISTS recording_channel (
        id INTEGER NOT NULL,
        recording_id INTEGER NOT NULL,
        channel VARCHAR(255) NOT NULL,
        audio_file VARCHAR(1024) NOT NULL,
        talker_id INTEGER,
        PRIMARY KEY (id),
        FOREIGN KEY(recording_id) REFERENCES recording (id),
        FOREIGN KEY(talker_id) REFERENCES talker (id)
    )"""


def schema_version(connection: sqlite3.Connection) -> int:
    """The version of the schema of the database as it is stored: 0 if it has none"""
    return connection.execute("PRAGMA user_version").fetchone()[0]


def check_version(connection: sqlite3.Connection, file: Path) -> int:
    """The schema version of a project database, which is the current one when the
    file has none. A database made by a newer phonlab raises ProjectError: what it
    has may not be what this version expects."""
    version = schema_version(connection)
    if version > SCHEMA_VERSION:
        raise ProjectError(
            f"{file} has schema version {version}, which is newer than the "
            f"{SCHEMA_VERSION} this version of phonlab knows; update phonlab"
        )
    return version or SCHEMA_VERSION


def create_tables(connection: sqlite3.Connection) -> None:
    """Make the tables every project has, if they are missing, and mark the file with
    the current schema version if it has none"""
    for statement in CORE_TABLES:
        connection.execute(statement)
    if schema_version(connection) == 0:
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}


def add_column(
    connection: sqlite3.Connection, table: str, name: str, sql_type: str
) -> None:
    """Add a column to a table if it does not have it, ignoring case as SQLite does
    (SQLite adds a column to a table that has rows without rewriting it)"""
    if name.casefold() not in {c.casefold() for c in table_columns(connection, table)}:
        connection.execute(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {sql_type}')


@contextmanager
def writing(path: str | Path, create: bool = False) -> Iterator[sqlite3.Connection]:
    """A connection to the database of a project that is written to: committed when the
    block ends, rolled back if it raises. `path` is the project folder or the file. A
    database that does not exist is an error unless `create`, which makes it (with its
    tables). A database that another program (the desktop app) is writing to at the
    moment raises ProjectError rather than waiting for it."""
    file = Path(path)
    if file.is_dir():
        file = file / DATABASE_FILENAME
    if not file.exists() and not create:
        raise ProjectError(f"There is no project database at {file}")
    connection = sqlite3.connect(file, timeout=LOCK_TIMEOUT)
    try:
        check_version(connection, file)
        create_tables(connection)
        yield connection
        connection.commit()
    except sqlite3.OperationalError as error:
        connection.rollback()
        if "locked" in str(error):
            raise ProjectError(
                f"{file} is in use by another program (the desktop app may have the "
                "project open); close it or try again"
            ) from error
        raise
    except sqlite3.DatabaseError as error:
        connection.rollback()
        raise ProjectError(f"{file} is not a project database: {error}") from error
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
