from typing import Any

from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync
from phonlab_project.columns import column_name, convert, infer_sql_type
from phonlab_project.metadata import MetadataColumn, MetadataTarget
from phonlab_project.readers.metadata_table import (
    MetadataColumnPlan,
    MetadataImportResult,
    MetadataMatch,
    MetadataTable,
)


class ImportMetadata(UseCaseSync[MetadataImportResult]):
    """Adds columns of a table to the project database, on the talkers or the
    recordings the rows were matched to. A column the database already has (from an
    earlier import of the same information) is updated, not duplicated. Empty cells
    stay empty."""

    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def plan_columns(
        self,
        table: MetadataTable,
        target: MetadataTarget,
        wanted: dict[str, str],
    ) -> list[MetadataColumnPlan]:
        """`wanted` maps the table's headers to the names the user wants. Names are
        made safe for the database and kept clear of the columns Phonlab itself
        uses."""
        reserved = {
            name.casefold()
            for name in self.annotation_repository.builtin_columns(target)
        }
        used: set[str] = set()
        plans: list[MetadataColumnPlan] = []
        for source, wanted_name in wanted.items():
            name = column_name(wanted_name or source, reserved | used)
            used.add(name.casefold())
            plans.append(
                MetadataColumnPlan(source, name, infer_sql_type(table.column(source)))
            )
        return plans

    def __call__(
        self,
        table: MetadataTable,
        match: MetadataMatch,
        plans: list[MetadataColumnPlan],
    ) -> MetadataImportResult:
        columns = [MetadataColumn(plan.name, plan.sql_type) for plan in plans]
        indexes = {plan.name: table.headers.index(plan.source) for plan in plans}
        types = {plan.name: plan.sql_type for plan in plans}

        values: dict[str, dict[str, Any]] = {}
        for row_index, key in match.matches.items():
            row = table.rows[row_index]
            values[key] = {
                name: convert(row[index], types[name])
                for name, index in indexes.items()
            }
        updated = self.annotation_repository.add_metadata(match.target, columns, values)
        return MetadataImportResult(
            n_rows=updated,
            columns=[column.name for column in columns],
        )
