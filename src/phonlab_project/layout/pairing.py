from dataclasses import replace

from phonlab_project.layout.project_scan import ScannedFile

SUFFIX_DELIMITERS = "_-."


def candidate_splits(stem: str) -> list[tuple[str, str]]:
    """Ways to read a file stem as (audio stem, suffix), longest audio stem first.
    The whole stem with an empty suffix always comes first."""
    splits = [(stem, "")]
    for idx in range(len(stem) - 1, 0, -1):
        if stem[idx] in SUFFIX_DELIMITERS:
            splits.append((stem[:idx], stem[idx:]))
    return splits


def reroot(file: ScannedFile, folder: str) -> ScannedFile:
    """The file as if `folder`, the folder its annotations are kept in, were a top-level
    folder next to the audio folders: ann/v1/t1/a.TextGrid in folder ann/v1 is
    paired like labels/t1/a.TextGrid"""
    relative = file.dir[len(folder) :].lstrip("/")
    return replace(file, dir=f"@/{relative}" if relative else "@")


def _tail(directory: str) -> str:
    return directory.partition("/")[2]


class AudioIndex:
    """Finds the audio file a given file belongs to. A file belongs to the audio
    file with the same name (ignoring case and extension) in the same folder, or,
    when the project keeps its kinds of files in parallel trees (audio/spk1/a.wav,
    annotations/spk1/a.TextGrid), the only audio file whose folder differs from the
    file's only in its first component."""

    def __init__(self, audio: list[ScannedFile]):
        self.by_dir: dict[tuple[str, str], ScannedFile] = {}
        self.by_tail: dict[tuple[str, str], list[ScannedFile]] = {}
        for file in audio:
            key = (file.dir, file.stem.casefold())
            self.by_dir.setdefault(key, file)
            self.by_tail.setdefault((_tail(file.dir), file.stem.casefold()), []).append(
                file
            )

    def owner(
        self, file: ScannedFile, allow_suffix: bool
    ) -> tuple[ScannedFile, str] | None:
        """The audio file `file` belongs to and the suffix between the audio stem and
        the extension. With `allow_suffix` False only whole-stem matches count."""
        for prefix, suffix in candidate_splits(file.stem):
            if suffix != "" and not allow_suffix:
                break
            prefix = prefix.casefold()
            same_dir = self.by_dir.get((file.dir, prefix))
            if same_dir is not None:
                return same_dir, suffix
            others = [
                audio
                for audio in self.by_tail.get((_tail(file.dir), prefix), [])
                if audio.dir != file.dir
            ]
            if len(others) == 1:
                return others[0], suffix
        return None
