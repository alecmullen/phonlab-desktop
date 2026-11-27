import csv
import io
from pathlib import Path

from core.base.use_case_sync import UseCaseSync
from phonlab_project.readers.metadata_table import MetadataTable

DELIMITERS = ",;\t|"
SNIFF_BYTES = 8192


class ReadMetadataCsv(UseCaseSync[MetadataTable]):
    """Reads a CSV file (comma, semicolon, tab or bar delimited, with or without a
    byte-order mark) whose first row names the columns.

    Raises ValueError if the file has no rows."""

    def __call__(self, path: str) -> MetadataTable:
        text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
        try:
            dialect = csv.Sniffer().sniff(text[:SNIFF_BYTES], delimiters=DELIMITERS)
        except csv.Error:
            dialect = csv.excel

        rows = [
            [cell.strip() for cell in row]
            for row in csv.reader(io.StringIO(text), dialect)
            if any(cell.strip() for cell in row)
        ]
        if len(rows) < 2:
            raise ValueError(
                "The file needs a row of column names and at least one row"
            )

        width = len(rows[0])
        headers = _unique_headers(rows[0])
        body = [(row + [""] * width)[:width] for row in rows[1:]]
        return MetadataTable(headers, body)


def _unique_headers(raw: list[str]) -> list[str]:
    headers: list[str] = []
    for index, header in enumerate(raw, start=1):
        name = header or f"column {index}"
        unique, number = name, 1
        while unique in headers:
            number += 1
            unique = f"{name} ({number})"
        headers.append(unique)
    return headers
