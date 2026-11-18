from dataclasses import dataclass, field


@dataclass(frozen=True)
class WordMatch:
    """How the words of a table line up with the words of a tier of the project"""

    tier: str
    n_rows: int = 0  # rows of the table with a word in the first column
    n_duplicates: int = 0  # rows whose word an earlier row has too
    n_words: int = 0  # different words in the tier
    n_found: int = 0  # of those, the words the table has
    # the words of the tier that the table lacks -> how often the tier has each
    unmatched: dict[str, int] = field(default_factory=dict)

    @property
    def n_unmatched(self) -> int:
        return len(self.unmatched)

    @property
    def n_extra(self) -> int:
        """Words of the table that the tier does not have"""
        return self.n_rows - self.n_duplicates - self.n_found


@dataclass(frozen=True)
class WordColumnPlan:
    """A column of the table to add to the word table"""

    source: str
    name: str
    sql_type: str  # as the database says it: INTEGER, REAL or TEXT


@dataclass(frozen=True)
class WordImportResult:
    n_rows: int = 0
    columns: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WordSource:
    """A table whose words were added to the project database, and how, so the same
    word table can be made again for a new database"""

    # the file, relative to the project directory if it is inside it
    file: str
    tier: str
    # header of each column added -> the name wanted for it in the database
    columns: dict[str, str] = field(default_factory=dict)
