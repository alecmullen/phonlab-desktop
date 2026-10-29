from data.database import Database


class DataSource:
    def __init__(self, database: Database):
        self.database = database
