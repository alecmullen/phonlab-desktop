from core.base.use_case_sync import UseCaseSync
from phonlab_project.readers.annotation_table import (
    audio_duration,
    load_table,
    number,
    resolve_unit,
    table_labels,
)
from phonlab_project.readers.table_format import (
    ColumnRole,
    TableFormat,
    TablePreview,
    TimeUnit,
)
from res.constants import TABLE_PREVIEW_ROWS


class PreviewAnnotationTable(UseCaseSync[TablePreview]):
    """Shows how a text file reads as a table of labelled intervals, for the user to
    check and correct. Each of `delimiter`, `skip` and `unit` that is given replaces
    what `table` (or, without one, the file) says."""

    def __call__(
        self,
        path: str,
        audio_path: str | None,
        table: TableFormat | None = None,
        delimiter: str | None = None,
        skip: int | None = None,
        unit: TimeUnit | None = None,
    ) -> TablePreview:
        loaded = load_table(path, audio_path, table, delimiter, skip, unit)
        duration = audio_duration(audio_path)

        columns = loaded.format.columns
        times = [
            t
            for role in (ColumnRole.START, ColumnRole.END)
            if role in columns
            for t in (number(row[columns.index(role)]) for row in loaded.rows)
            if t is not None
        ]
        problem = ""
        try:
            table_labels(loaded, duration)
        except ValueError as err:
            problem = str(err)
        return TablePreview(
            loaded.format,
            loaded.names,
            loaded.rows[:TABLE_PREVIEW_ROWS],
            len(loaded.rows),
            resolve_unit(loaded.format.unit, times, duration),
            problem,
        )
