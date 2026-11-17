from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from data.base.base_entity import BaseEntity
from res.constants import PROJECT_DATABASE_FILENAME


class Database:
    engine: Engine

    def open_session(self) -> Session:
        return Session(self.engine)

    def reset(self) -> str | None:
        """Replace the database with a new empty one, returning the path of the
        backup of the old one"""
        raise NotImplementedError


class SQLiteDatabase(Database):
    def connect(self, dir_path: str):
        self.dir_path = dir_path
        self.engine = create_engine(
            f"sqlite:///{Path(dir_path) / PROJECT_DATABASE_FILENAME}", echo=True
        )
        BaseEntity.metadata.create_all(self.engine)

    def reset(self) -> str | None:
        """Move the database file aside as a timestamped backup and start a new one.
        Anything holding this object keeps working, as it is reconnected in place"""
        self.engine.dispose()

        backup = None
        database_file = Path(self.dir_path) / PROJECT_DATABASE_FILENAME
        if database_file.exists():
            stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            backup_file = database_file.with_name(
                f"{database_file.stem}.{stamp}.db.bak"
            )
            suffix = 1
            while backup_file.exists():  # never overwrite an earlier backup
                backup_file = database_file.with_name(
                    f"{database_file.stem}.{stamp}-{suffix}.db.bak"
                )
                suffix += 1
            database_file.replace(backup_file)
            backup = str(backup_file)

        self.connect(self.dir_path)
        return backup
