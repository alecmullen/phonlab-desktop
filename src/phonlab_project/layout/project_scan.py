from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScannedFile:
    """A file in the project, located by its path relative to the project
    directory (forward slashes). `ext` is casefolded and includes the dot."""

    path: str
    dir: str
    name: str
    stem: str
    ext: str

    @classmethod
    def from_path(cls, path: str) -> "ScannedFile":
        directory, _, name = path.rpartition("/")
        stem, dot, ext = name.rpartition(".")
        if dot == "" or stem == "":
            stem, ext = name, ""
        else:
            ext = "." + ext.casefold()
        return cls(path=path, dir=directory, name=name, stem=stem, ext=ext)

    @property
    def path_without_ext(self) -> str:
        return self.path[: len(self.path) - len(self.ext)]


@dataclass(frozen=True)
class ProjectScan:
    root: str
    files: list[ScannedFile] = field(default_factory=list)
