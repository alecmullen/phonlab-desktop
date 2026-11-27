import csv
import math
from pathlib import Path

import soundfile as sf

from phonlab_project.readers.table_format import (
    WHITESPACE,
    ColumnRole,
    LoadedTable,
    TableFormat,
    TimeUnit,
)
from res.constants import TABLE_MAX_HEADER_LINES, TIER_TABLE_DURATION_SLACK


def read_lines(path: str) -> list[str]:
    """The lines of a text file that have something in them"""
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    return [line for line in text.splitlines() if line.strip() != ""]


def audio_duration(audio_path: str | None) -> float | None:
    if audio_path is None:
        return None
    try:
        return float(sf.info(audio_path).duration)
    except (RuntimeError, ValueError):
        return None


def number(text: str) -> float | None:
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def detect_delimiter(lines: list[str]) -> str:
    for delimiter in ("\t", ","):
        if sum(delimiter in line for line in lines) >= len(lines) / 2:
            return delimiter
    return WHITESPACE


def split_row(line: str, delimiter: str, n_columns: int | None = None) -> list[str]:
    """The fields of a line. With WHITESPACE and `n_columns`, the last field is the rest
    of the line"""
    if delimiter == WHITESPACE:
        fields = line.split(None, n_columns - 1) if n_columns else line.split()
    elif delimiter == ",":
        fields = next(csv.reader([line]))
    else:
        fields = line.split(delimiter)
    return [field.strip() for field in fields]


def guess_skip(lines: list[str], delimiter: str) -> int:
    """How many lines come before the data: the fewest after which every line has
    at least two fields and some column is all numbers"""
    for skip in range(min(len(lines), TABLE_MAX_HEADER_LINES + 1)):
        rows = [split_row(line, delimiter) for line in lines[skip:]]
        if not rows or min(len(row) for row in rows) < 2:
            continue
        width = min(len(row) for row in rows)
        if any(all(number(row[c]) is not None for row in rows) for c in range(width)):
            return skip
    return 0


def guess_n_columns(lines: list[str], delimiter: str) -> int:
    """How many columns a table has. With WHITESPACE, when the same number of numbers
    begins every line and more than one word follows on some line, they are one
    column: the label."""
    rows = [split_row(line, delimiter) for line in lines]
    if delimiter == WHITESPACE:
        prefixes = {_numeric_prefix(row) for row in rows}
        if len(prefixes) == 1:
            (prefix,) = prefixes
            if prefix >= 1 and any(len(row) > prefix + 1 for row in rows):
                return prefix + 1
    widths = [len(row) for row in rows]
    return max(set(widths), key=widths.count)


def _numeric_prefix(row: list[str]) -> int:
    count = 0
    for field in row:
        if number(field) is None:
            break
        count += 1
    return count


def load_table(
    path: str,
    audio_path: str | None,
    table: TableFormat | None = None,
    delimiter: str | None = None,
    skip: int | None = None,
    unit: TimeUnit | None = None,
) -> LoadedTable:
    """Reads a text file as a table. Each of `table`, `delimiter`, `skip` and `unit`
    that is not given is worked out from the file, except that what `table` says is
    kept as long as what comes before it in this list is as it says. Raises ValueError
    if the file has nothing in it."""
    lines = read_lines(path)
    if not lines:
        raise ValueError(f"Nothing to read in {path}")

    delim = delimiter or (table.delimiter if table else detect_delimiter(lines))
    same_delimiter = table is not None and delim == table.delimiter
    if skip is not None:
        n_skip = skip
    elif table is not None and same_delimiter:
        n_skip = table.skip
    else:
        n_skip = guess_skip(lines, delim)
    data = lines[n_skip:]
    if not data:
        raise ValueError(f"No data after {n_skip} lines of {path}")

    same_layout = table is not None and same_delimiter and n_skip == table.skip
    n_columns = (
        len(table.columns)
        if table is not None and same_layout and table.columns
        else guess_n_columns(data, delim)
    )
    fixed = n_columns if delim == WHITESPACE else None
    rows = [split_row(line, delim, fixed) for line in data]
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]

    # the line before the data names the columns if it has a name for each (for spaces
    # as delimiter, only if it is the one line before the data: more lines are likely
    # to be text, such as END OF HEADER)
    names: tuple[str, ...] = ()
    if n_skip > 0 and (delim != WHITESPACE or n_skip == 1):
        above = split_row(lines[n_skip - 1], delim, fixed)
        if len(above) == width and any(number(field) is None for field in above):
            names = tuple(above)

    chosen_unit = unit or (table.unit if table else TimeUnit.AUTO)
    if table is not None and same_layout and len(table.columns) == width:
        columns = table.columns
    else:
        columns = guess_columns(rows, audio_duration(audio_path), chosen_unit)
    return LoadedTable(TableFormat(delim, n_skip, columns, chosen_unit), names, rows)


def guess_columns(
    rows: list[list[str]], duration: float | None, unit: TimeUnit
) -> tuple[ColumnRole, ...]:
    """What each column is. A column that is all numbers within the length of the audio
    (in the unit given, or in either) is a time. The time column with the smallest values
    is the start and, if it is never less than the start, the one with the largest is the
    end; any others are unknown. The label is the first column that is not a time, a
    text one if there is one."""
    width = len(rows[0])
    numbers: dict[int, list[float]] = {}  # the columns that are all numbers
    for c in range(width):
        column = [number(row[c]) for row in rows]
        if all(value is not None for value in column):
            numbers[c] = [value for value in column if value is not None]
    times = [c for c, values in numbers.items() if _is_time(values, duration, unit)]

    roles = [ColumnRole.UNKNOWN] * width
    if times:
        by_size = sorted(times, key=lambda c: sum(numbers[c]))
        start = by_size[0]
        roles[start] = ColumnRole.START
        if len(by_size) > 1:
            end = by_size[-1]
            if all(b <= e for b, e in zip(numbers[start], numbers[end])):
                roles[end] = ColumnRole.END

    others = [c for c in range(width) if c not in times]
    for c in [c for c in others if c not in numbers] or others:
        roles[c] = ColumnRole.LABEL
        break
    return tuple(roles)


def _is_time(values: list[float], duration: float | None, unit: TimeUnit) -> bool:
    if min(values) < 0:
        return False
    if duration is None:
        return True
    limit = duration * TIER_TABLE_DURATION_SLACK
    if unit is TimeUnit.SECONDS:
        return max(values) <= limit
    if unit is TimeUnit.MILLISECONDS:
        return max(values) / 1000 <= limit
    return max(values) <= limit or max(values) / 1000 <= limit


def resolve_unit(
    unit: TimeUnit, times: list[float], duration: float | None
) -> TimeUnit:
    """SECONDS or MILLISECONDS: the unit given, or else the one that makes the times
    fit the length of the audio (seconds if there is no telling)"""
    if unit is not TimeUnit.AUTO:
        return unit
    if duration is None or not times:
        return TimeUnit.SECONDS
    limit = duration * TIER_TABLE_DURATION_SLACK
    if max(times) <= limit:
        return TimeUnit.SECONDS
    return TimeUnit.MILLISECONDS if max(times) / 1000 <= limit else TimeUnit.SECONDS


def table_labels(
    loaded: LoadedTable, duration: float | None
) -> list[tuple[float, float, str]]:
    """The (begin, end, text) of each row of a table, with the times in seconds. A table
    with no end times ends each label where the next begins, and the last one at the end
    of the audio. Raises ValueError for a table that cannot be read like that."""
    columns = loaded.format.columns
    if ColumnRole.START not in columns:
        raise ValueError("No column is the start time of the labels")
    start = columns.index(ColumnRole.START)
    end = columns.index(ColumnRole.END) if ColumnRole.END in columns else None
    label = columns.index(ColumnRole.LABEL) if ColumnRole.LABEL in columns else None

    begins, ends, texts = [], [], []
    for row in loaded.rows:
        begin = number(row[start])
        finish = number(row[end]) if end is not None else None
        if begin is None or (end is not None and finish is None):
            raise ValueError(f"Cannot read a time in line: {' '.join(row)!r}")
        begins.append(begin)
        ends.append(finish)
        texts.append(row[label] if label is not None else "")

    scale = (
        0.001
        if resolve_unit(
            loaded.format.unit,
            [t for t in [*begins, *ends] if t is not None],
            duration,
        )
        is TimeUnit.MILLISECONDS
        else 1.0
    )
    labels = []
    for i, (begin, finish, text) in enumerate(zip(begins, ends, texts)):
        if finish is None:
            if i + 1 < len(begins):
                finish = begins[i + 1]
            else:
                finish = max(duration / scale, begin) if duration is not None else begin
        labels.append((begin * scale, finish * scale, text))
    return labels
