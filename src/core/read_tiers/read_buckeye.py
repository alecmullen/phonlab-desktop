import re
from pathlib import Path
from typing import Any

from core.read_tiers.sibling_file import find_sibling

HEADER_END = re.compile(r"#\r?\n")
WORD_FIELDS = re.compile(r"; | \d{3} ")
PHONE_FIELDS = re.compile(r"\s+\d{3}\s+")
PHONE_LABEL_END = re.compile(r" ?;| ?\+")


def read_buckeye_tiers(words_path: str) -> list[dict[str, Any]]:
    """Reads a Buckeye corpus .words file, and the .phones file next to it if there
    is one, into a `word` tier and a `phone` tier. Both files list the end time of
    each interval; an interval begins where the one before it ends."""
    tiers = [{"name": "word", "labels": _read_words(words_path)}]

    phones_path = find_sibling(words_path, ".phones")
    if phones_path is not None:
        tiers.append({"name": "phone", "labels": _read_phones(phones_path)})
    return tiers


def _body(path: str) -> list[str]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    parts = HEADER_END.split(text, maxsplit=1)
    if len(parts) < 2:
        raise ValueError(f"{path} is not a Buckeye file: no '#' line ends its header")
    return parts[1].splitlines()


def _read_words(path: str) -> list[tuple[float, float, str]]:
    labels: list[tuple[float, float, str]] = []
    begin = 0.0
    for line in _body(path):
        if line.strip() == "":
            continue
        fields = WORD_FIELDS.split(line.strip())
        try:
            end = float(fields[0])
            word = fields[1].replace(" ", "_")
        except (ValueError, IndexError) as err:
            raise ValueError(f"Cannot read line of {path}: {line!r}") from err
        labels.append((begin, end, word))
        begin = end
    return labels


def _read_phones(path: str) -> list[tuple[float, float, str]]:
    labels: list[tuple[float, float, str]] = []
    begin = 0.0
    for line in _body(path):
        fields = PHONE_FIELDS.split(line.strip())
        try:
            end = float(fields[0])
        except ValueError:
            continue
        if len(fields) < 2:
            continue  # an end time with no label
        labels.append((begin, end, PHONE_LABEL_END.split(fields[1])[0]))
        begin = end
    return labels
