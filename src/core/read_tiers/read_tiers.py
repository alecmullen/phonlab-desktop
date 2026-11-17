from pathlib import Path
from typing import Any

import phonlab as phon

from core.read_tiers.read_buckeye import read_buckeye_tiers
from core.read_tiers.read_timit import read_timit_tiers


def read_tiers(file_path: str) -> list[dict[str, Any]]:
    """Reads the tiers of an annotation file, whatever its format is, as the
    reader of Praat TextGrids does: a list of dicts with a `name` and `labels`,
    a list of (begin, end, text) tuples. Buckeye (.words, with its .phones) and
    TIMIT (.wrd, with its .phn) files are read into a word tier and a phone tier."""
    ext = Path(file_path).suffix.casefold()
    if ext == ".words":
        return read_buckeye_tiers(file_path)
    if ext == ".wrd":
        return read_timit_tiers(file_path)
    return phon.read_textgrid_with(file_path)
