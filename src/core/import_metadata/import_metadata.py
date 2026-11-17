import re
from typing import Any

from core.annotation.entity.metadata import MetadataColumn, MetadataTarget, SqlType
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync
from core.import_metadata.entity.metadata_table import (
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


def column_name(raw: str, taken: set[str]) -> str:
    """A name for a database column made from `raw`: letters, digits and
    underscores only, not starting with a digit, and different (ignoring case)
    from the names in `taken`"""
    name = re.sub(r"[^0-9A-Za-z]+", "_", raw.strip()).strip("_") or "column"
    if name[0].isdigit():
        name = f"c_{name}"
    unique, number = name, 1
    while unique.casefold() in taken:
        number += 1
        unique = f"{name}_{number}"
    return unique


def infer_sql_type(values: list[str]) -> SqlType:
    filled = [value for value in values if value != ""]
    if filled and all(_is_int(value) for value in filled):
        return SqlType.INTEGER
    if filled and all(_is_float(value) for value in filled):
        return SqlType.REAL
    return SqlType.TEXT


def convert(value: str, sql_type: SqlType) -> int | float | str | None:
    if value == "":
        return None
    if sql_type == SqlType.INTEGER:
        return int(value)
    if sql_type == SqlType.REAL:
        return float(value)
    return value


def _is_int(value: str) -> bool:
    try:
        int(value)
    except ValueError:
        return False
    return True


def _is_float(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True
