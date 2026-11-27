"""What a project says about the corpus as a whole (its title, who made it, how to cite
it), kept in the `[corpus]` section of the project's `phonlab.toml`:

.. code-block:: toml

    [corpus]
    title = "CABank CORAAL Corpus"
    creator = ["Kendall, Tyler", "Farrington, Charlie"]   # a list when there are several
    language = "eng"
    doi = "10.21415/V68B-VW06"

The names are free, and the values are text or a list of texts. The section can be
written by hand, or is copied from a corpus description file the project folder has
(TalkBank's `0metadata.cdc`) when the project is imported."""

import os
import tomllib
from pathlib import Path

import tomli_w

from phonlab_project.constants import CORPUS_DESCRIPTION_SUFFIXES, CORPUS_TOML_KEY

TOML_NAME = "phonlab.toml"

CorpusInfo = dict[str, str | list[str]]


def read_corpus_description(path: str | Path) -> CorpusInfo:
    """Read a corpus description file, as TalkBank corpora have (`0metadata.cdc`).

    Each line is a name and a value separated by a tab (`Title:<tab>CABank CORAAL
    Corpus`). The names are made lower case, and a name that appears more than once
    (several creators) gives a list.

    Parameters
    ----------

    path : path-like
        The description file.

    Returns
    -------

    info : dict
        Name -> text, or a list of text for a name that is repeated. Lines that do not
        have a name and a value are left out.

    Raises
    ------

    OSError
        If the file cannot be opened.

    Examples
    --------

    >>> read_corpus_description("0metadata.cdc")["title"]  # doctest: +SKIP
    'CABank CORAAL Corpus'"""
    info: CorpusInfo = {}
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    for line in text.splitlines():
        name, tab, value = line.partition("\t")
        name, value = name.strip().rstrip(":").strip().casefold(), value.strip()
        if not tab or not name or not value:
            continue
        name = "_".join(name.split())
        before = info.get(name)
        if before is None:
            info[name] = value
        elif isinstance(before, list):
            before.append(value)
        else:
            info[name] = [before, value]
    return info


def load_corpus(dir_path: str | Path) -> CorpusInfo:
    """Read what a project says about its corpus, from `[corpus]` in its `phonlab.toml`.

    Parameters
    ----------

    dir_path : path-like
        The project folder.

    Returns
    -------

    info : dict
        Name -> text (or a list of texts). Empty if there is no `phonlab.toml` or it has
        no `[corpus]`.

    Examples
    --------

    >>> load_corpus("my_corpus").get("title")  # doctest: +SKIP"""
    try:
        with open(Path(dir_path) / TOML_NAME, "rb") as f:
            section = tomllib.load(f).get(CORPUS_TOML_KEY)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    if not isinstance(section, dict):
        return {}
    return {
        str(name): value
        for name, value in section.items()
        if isinstance(value, str)
        or (isinstance(value, list) and all(isinstance(v, str) for v in value))
    }


def save_corpus(dir_path: str | Path, info: CorpusInfo) -> None:
    """Save what a project says about its corpus in `[corpus]` of its `phonlab.toml`,
    replacing what was there and keeping the file's other settings.

    Parameters
    ----------

    dir_path : path-like
        The project folder.

    info : dict
        Name -> text, or a list of texts."""
    path = Path(dir_path) / TOML_NAME
    data: dict = {}
    if path.exists():
        with open(path, "rb") as f:
            data = tomllib.load(f)
    data[CORPUS_TOML_KEY] = dict(info)
    with open(path, "wb") as f:
        tomli_w.dump(data, f)


def adopt_corpus_description(dir_path: str | Path) -> bool:
    """Copies the corpus description file a project folder has into `[corpus]` of its
    `phonlab.toml`, unless the section is already there (what a person wrote is kept).
    The file is looked for in the folder and the folders directly inside it, and the
    first by name is used. Returns whether anything was saved."""
    folder = Path(dir_path)
    if load_corpus(folder):
        return False
    for directory in _directories(folder):
        for name in sorted(os.listdir(directory)):
            if name.startswith(".") or Path(name).suffix.casefold() not in (
                CORPUS_DESCRIPTION_SUFFIXES
            ):
                continue
            try:
                info = read_corpus_description(directory / name)
            except OSError:
                continue
            if info:
                save_corpus(folder, info)
                return True
    return False


def _directories(folder: Path) -> list[Path]:
    try:
        inside = sorted(p for p in folder.iterdir() if p.is_dir())
    except OSError:
        return [folder]
    return [folder, *(p for p in inside if not p.name.startswith("."))]
