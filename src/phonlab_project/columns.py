"""Names and types for the columns a researcher adds to talkers and words from a table."""

import re

from phonlab_project.metadata import SqlType


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
