from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync
from core.inspect_database.entity.table_data import TableData


class ListTables(UseCaseSync[list[str]]):
    """The tables of the project database, the ones about recordings and talkers
    first"""

    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(self) -> list[str]:
        return self.annotation_repository.list_tables()


class ReadTable(UseCaseSync[TableData]):
    """Reads the first `limit` rows of a table, with all its columns, including
    those added from CSV files. Nothing is changed.

    Raises ValueError if the database has no such table."""

    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(self, name: str, limit: int) -> TableData:
        return self.annotation_repository.read_table(name, limit)
