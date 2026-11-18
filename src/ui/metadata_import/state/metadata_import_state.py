from dataclasses import dataclass, field

from ui.base.state import State


@dataclass
class MetadataColumnState(State):
    source: str
    name: str  # the name the column will have in the database
    sql_type: str
    example: str
    selected: bool


@dataclass
class MetadataImportState(State):
    """Everything the dialog for adding information from a CSV file shows"""

    file_name: str = ""
    target: str = "talker"  # "talker" or "recording"
    target_locked: bool = False  # the user is not asked what the rows are about
    key_column: str = ""
    key_columns: list[str] = field(default_factory=list)

    n_rows: int = 0
    n_matched: int = 0
    n_targets: int = 0
    n_unmatched_targets: int = 0
    n_duplicates: int = 0
    strategy: str = ""
    unmatched_examples: list[str] = field(default_factory=list)
    unmatched_target_examples: list[str] = field(default_factory=list)

    columns: list[MetadataColumnState] = field(default_factory=list)
    can_import: bool = False
