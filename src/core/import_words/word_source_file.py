import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from core.base.use_case_sync import UseCaseSync
from core.import_metadata.information_sources_file import TOML_NAME
from core.import_words.entity.word_table import WordSource
from res.constants import WORDS_TOML_KEY


class LoadWordSource(UseCaseSync[WordSource | None]):
    """The table whose words were added to the project, or None if there was none (or
    what the project file says about it cannot be understood)"""

    def __call__(self, dir_path: str) -> WordSource | None:
        try:
            with open(Path(dir_path) / TOML_NAME, "rb") as f:
                entry = tomllib.load(f).get(WORDS_TOML_KEY)
            if not isinstance(entry, dict):
                return None
            return WordSource(
                file=str(entry["file"]),
                tier=str(entry["tier"]),
                columns={str(k): str(v) for k, v in entry.get("columns", {}).items()},
            )
        except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError, AttributeError):
            return None


class SaveWordSource(UseCaseSync[None]):
    """Remembers in the project file the table whose words were added, replacing what it
    remembered, and keeping the rest of the project file"""

    def __call__(self, dir_path: str, source: WordSource) -> None:
        path = Path(dir_path) / TOML_NAME
        data: dict[str, Any] = {}
        if path.exists():
            with open(path, "rb") as f:
                data = tomllib.load(f)
        data[WORDS_TOML_KEY] = {
            "file": source.file,
            "tier": source.tier,
            "columns": dict(source.columns),
        }
        with open(path, "wb") as f:
            tomli_w.dump(data, f)
