from pathlib import Path


def find_sibling(path: str, ext: str) -> str | None:
    """The file next to `path` with the same stem and extension `ext`, matching
    the case of the extension of `path` (corpora use .WRD/.PHN as often as
    .wrd/.phn), or else any case. None if there is no such file."""
    source = Path(path)
    ext = ext.upper() if source.suffix.isupper() else ext.lower()
    direct = source.with_suffix(ext)
    if direct.exists():
        return str(direct)
    wanted = (source.stem + ext).casefold()
    for other in source.parent.iterdir():
        if other.name.casefold() == wanted:
            return str(other)
    return None
