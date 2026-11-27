from typing import Any

from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync
from core.import_words.entity.word_table import WordColumnPlan, WordImportResult
from phonlab_project.columns import column_name, convert, infer_sql_type
from phonlab_project.metadata import MetadataColumn, SqlType
from phonlab_project.readers.metadata_table import MetadataTable

# what the word table has before any column of the table is added to it
BUILTIN_WORD_COLUMNS = ("id", "word")


class ImportWords(UseCaseSync[WordImportResult]):
    """Makes the word table of the project database from a table with a row for each
    word: the first column has the words, and every other column becomes a column of
    the word table, as numbers if all its values are, else as text. A word table the
    database already has is replaced. Empty cells stay empty, and a word that a later
    row has again is taken from the first row that has it."""

    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def plan_columns(
        self, table: MetadataTable, wanted: dict[str, str] | None = None
    ) -> list[WordColumnPlan]:
        """The columns to add: every column but the first, or those of `wanted` (header
        -> the name wanted), with names made safe for the database"""
        taken = set(BUILTIN_WORD_COLUMNS)
        plans: list[WordColumnPlan] = []
        for header in table.headers[1:]:
            if wanted is not None and header not in wanted:
                continue
            name = column_name((wanted or {}).get(header) or header, taken)
            taken.add(name.casefold())
            plans.append(
                WordColumnPlan(header, name, infer_sql_type(table.column(header)).value)
            )
        return plans

    def __call__(
        self, table: MetadataTable, plans: list[WordColumnPlan]
    ) -> WordImportResult:
        columns = [MetadataColumn(plan.name, SqlType(plan.sql_type)) for plan in plans]
        indexes = {plan.name: table.headers.index(plan.source) for plan in plans}

        rows: dict[str, dict[str, Any]] = {}
        for row in table.rows:
            word = row[0]
            if word == "" or word in rows:
                continue
            rows[word] = {
                column.name: convert(row[indexes[column.name]], column.sql_type)
                for column in columns
            }
        written = self.annotation_repository.replace_words(columns, list(rows.items()))
        return WordImportResult(written, [column.name for column in columns])
