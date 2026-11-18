import tomllib
from pathlib import Path

import tomli_w


def read_toml(path: Path) -> dict:
    """The contents of a TOML file, or an empty dict if it is missing or malformed"""
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def write_toml_values(path: Path, section: str, values: dict[str, object | None]):
    """Set the keys of `values` in `[section]` of a TOML file, keeping its other
    contents. A value of None removes the key"""
    contents = read_toml(path)
    table = contents.get(section)
    if not isinstance(table, dict):
        table = {}
    for key, value in values.items():
        if value is None:
            table.pop(key, None)
        else:
            table[key] = value
    contents[section] = table

    with open(path, "wb") as f:
        tomli_w.dump(contents, f)
