from pathlib import Path


def make_tree(root: Path, paths: list[str]) -> Path:
    """Creates an empty file for every relative path, with its folders"""
    for path in paths:
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b"")
    return root


def talker_tree(
    root: Path,
    talkers: tuple[str, ...] = ("aa1", "bb2"),
    items: int = 4,
    annotated: int | None = None,
    data_kinds: tuple[str, ...] = (".trk", ".pos"),
) -> Path:
    """A project with a folder per talker, each holding `items` recordings named
    like <talker>_<n>.wav. The first `annotated` of them (all by default) have a
    .TextGrid, and every one has a file of each kind in `data_kinds`."""
    annotated = items if annotated is None else annotated
    paths = []
    for talker in talkers:
        for n in range(1, items + 1):
            stem = f"{talker}/{talker}_{n:02d}"
            paths.append(f"{stem}.wav")
            if n <= annotated:
                paths.append(f"{stem}.TextGrid")
            paths.extend(f"{stem}{kind}" for kind in data_kinds)
        paths.append(f"{talker}/notes.csv")
    return make_tree(root, paths)


def write_audio_like(root: Path, path: str, size: int) -> None:
    """An audio file of `size` bytes (not readable as audio)"""
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(bytes(size))
