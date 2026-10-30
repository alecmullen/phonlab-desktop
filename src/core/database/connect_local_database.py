from core.base.use_case_sync import UseCaseSync
from core.database.local_database import LocalDatabase


class ConnectLocalDatabase(UseCaseSync):
    def __init__(self, database: LocalDatabase):
        self.database = database

    def __call__(self, dir_path: str):
        self.database.connect(dir_path)
