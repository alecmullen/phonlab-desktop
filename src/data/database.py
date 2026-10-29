from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session


class Database:
    engine: Engine

    def open_session(self) -> Session:
        return Session(self.engine)


class SQLiteDatabase(Database):
    def __init__(self, dir_path: str):
        self.engine = create_engine(f"sqlite:///{dir_path}", echo=True)
