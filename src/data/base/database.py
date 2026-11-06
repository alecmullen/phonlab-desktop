from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from core.database.local_database import LocalDatabase
from data.base.base_entity import BaseEntity


class Database:
    engine: Engine

    def open_session(self) -> Session:
        return Session(self.engine)


class SQLiteDatabase(Database, LocalDatabase):
    def connect(self, dir_path: str):
        self.engine = create_engine(f"sqlite:///{dir_path}/phonlab.db", echo=True)
        BaseEntity.metadata.create_all(self.engine)
