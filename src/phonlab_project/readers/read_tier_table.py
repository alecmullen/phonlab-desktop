from typing import Any

from phonlab_project.readers.annotation_table import (
    audio_duration,
    load_table,
    table_labels,
)
from phonlab_project.readers.table_format import TableFormat


def read_tier_table(
    path: str,
    tier_name: str,
    audio_path: str | None = None,
    table: TableFormat | None = None,
) -> dict[str, Any]:
    """Reads a text file of labelled intervals, as a table, into a tier called
    `tier_name` in the form of the TextGrid reader: a dict with a `name` and `labels`,
    a list of (begin, end, text) tuples with the times in seconds. `table` says how to
    read the file (its delimiter, the columns...); without it that is worked out from
    the file and the length of the audio file `audio_path`. Raises ValueError for a file
    that cannot be read as a tier."""
    loaded = load_table(path, audio_path, table)
    return {
        "name": tier_name,
        "labels": table_labels(loaded, audio_duration(audio_path)),
    }
