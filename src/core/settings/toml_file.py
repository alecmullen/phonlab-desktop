import tomllib
from pathlib import Path


def read_toml(path: Path) -> dict:
    """The contents of a TOML file, or an empty dict if it is missing or malformed"""
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
