import os
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from data.base.base_entity import ON_DEMAND, BaseEntity
from res.constants import PROJECT_DATABASE_FILENAME


class Database:
    engine: Engine

    def open_session(self) -> Session:
        return Session(self.engine)

    def reset(self) -> str | None:
        """Replace the database with a new empty one, returning the path of the
        backup of the old one"""
        raise NotImplementedError

    def close(self) -> None:
        """Release the connections to the database"""
        raise NotImplementedError


class SQLiteDatabase(Database):
    def connect(self, dir_path: str):
        self.dir_path = dir_path
        self.engine = create_engine(
            f"sqlite:///{Path(dir_path) / PROJECT_DATABASE_FILENAME}",
            # Logging every statement slows large imports down a great deal, so it is
            # only done when asked for (to see what the app does: PHONLAB_SQL_ECHO=1)
            echo=os.environ.get("PHONLAB_SQL_ECHO") == "1",
        )
        BaseEntity.metadata.create_all(
            self.engine,
            tables=[
                table
                for table in BaseEntity.metadata.sorted_tables
                if not table.info.get(ON_DEMAND)
            ],
        )

    def close(self):
        """Close every connection to the database file. The engine reconnects if it is
        used again"""
        self.engine.dispose()

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
