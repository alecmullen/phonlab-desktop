from pathlib import Path
from typing import Any

import phonlab as phon

from phonlab_project.readers.read_buckeye import read_buckeye_tiers
from phonlab_project.readers.read_elan import read_elan_tiers
from phonlab_project.readers.read_srt import read_srt_tiers
from phonlab_project.readers.read_timit import read_timit_tiers


def read_tiers(file_path: str) -> list[dict[str, Any]]:
    """Read the tiers of an annotation file, whatever its format, as dicts.

    The format is taken from the extension: `.TextGrid`, `.eaf` (ELAN), `.srt`
    (subtitles), `.words` (Buckeye, with its `.phones` file) or `.wrd` (TIMIT, with its
    `.phn` file). Anything else is read as a Praat TextGrid. `read_annotation` gives the
    same labels as a DataFrame.

    Parameters
    ----------

    file_path : str
        The annotation file.

    Returns
    -------

    tiers : list of dict
        One dict per tier, with `name`, `labels` (a list of `(begin, end, text)` in
        seconds; `end` is None for a point) and, where the file says who made the tier,
        `talker`. A Praat TextGrid gives the dicts `phonlab.read_textgrid_with` does.
        Buckeye and TIMIT files give a `word` and a `phone` tier.

    Raises
    ------

    OSError
        If the file cannot be opened.

    ValueError
        If the file cannot be read as its format."""
    ext = Path(file_path).suffix.casefold()
    if ext == ".words":
        return read_buckeye_tiers(file_path)
    if ext == ".wrd":
        return read_timit_tiers(file_path)
    if ext == ".eaf":
        return read_elan_tiers(file_path)
    if ext == ".srt":
        return read_srt_tiers(file_path)
    return phon.read_textgrid_with(file_path)
