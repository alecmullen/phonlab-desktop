from dataclasses import dataclass, field

from ui.base.state import State


@dataclass
class WordColumnState(State):
    source: str
    name: str  # the name the column will have in the database
    sql_type: str
    example: str


@dataclass
class WordImportState(State):
    """Everything the dialog for adding a table of words shows"""

    file_name: str = ""
    key_column: str = ""  # the header of the first column, which has the words
    tier: str = ""
    tiers: list[str] = field(default_factory=list)

    n_rows: int = 0  # words in the table
    n_duplicates: int = 0
    n_words: int = 0  # different words in the tier
    n_found: int = 0  # of those, the words in the table
    n_unmatched: int = 0  # the words of the tier that the table lacks
    n_extra: int = 0  # words of the table that the tier does not have
    unmatched_examples: list[str] = field(default_factory=list)

    columns: list[WordColumnState] = field(default_factory=list)
    can_import: bool = False
