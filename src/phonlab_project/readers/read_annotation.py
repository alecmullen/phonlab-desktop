from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from phonlab_project.constants import ANNOTATION_FORMATS
from phonlab_project.errors import ProjectError
from phonlab_project.readers.read_tiers import read_tiers

COLUMNS = ["tier", "talker", "t1", "t2", "label"]


def read_annotation(
    path: str | Path, tier: str | Sequence[str] | None = None
) -> pd.DataFrame:
    """Read the labels of an annotation file, whatever its format, into a DataFrame.

    The format is taken from the file's extension (case does not matter):
    `.TextGrid` (Praat), `.eaf` (ELAN), `.srt` (subtitles), `.cha` (CHAT, as TalkBank corpora have), `.words` (Buckeye,
    read with its `.phones` file) and `.wrd` (TIMIT, read with its `.phn` file).

    Parameters
    ----------

    path : path-like
        The annotation file.

    tier : str or sequence of str, optional
        The tiers to read. All of them by default.

    Returns
    -------

    labels : pandas.DataFrame
        One row for each label, tiers in the order of the file and labels in the
        order of their tier, with columns `tier`, `talker`, `t1`, `t2` and
        `label`. `t1` and `t2` are the start and end of the label in seconds; a
        label that is a point (a Praat point tier) has `t2` equal to `t1`.
        `talker` is who made the tier where the file says (an ELAN participant,
        the talker a subtitle names) and `None` where it does not. These are the
        columns `Project.labels()` gives, without `recording`.

    Raises
    ------

    ProjectError
        If the extension is not one of those above, or `tier` names a tier the
        file lacks (the message lists the tiers it has).

    OSError
        If the file cannot be opened.

    ValueError
        If the file cannot be read as the format its extension says.

    Examples
    --------

    >>> words = read_annotation("S24-003.srt")
    >>> words[words.talker == "Camille"].label.str.split().str.len().sum()  # doctest: +SKIP

    See Also
    --------

    read_tiers : the same tiers as a list of dicts, as `phonlab.read_textgrid_with`
        gives them.
    """
    file = Path(path)
    if file.suffix.casefold() not in ANNOTATION_FORMATS:
        raise ProjectError(
            f"Cannot read {file.name}: annotation files are {sorted(ANNOTATION_FORMATS)}"
        )
    tiers = read_tiers(str(file))

    if tier is not None:
        wanted = [tier] if isinstance(tier, str) else list(tier)
        names = [t["name"] for t in tiers]
        if missing := [name for name in wanted if name not in names]:
            raise ProjectError(f"{file.name} has no tier {missing}; it has {names}")
        tiers = [t for t in tiers if t["name"] in wanted]

    rows = [
        (t["name"], t.get("talker"), begin, begin if end is None else end, text)
        for t in tiers
        for begin, end, text in t["labels"]
    ]
    return pd.DataFrame(rows, columns=COLUMNS).astype({"t1": float, "t2": float})
