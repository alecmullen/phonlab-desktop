from pathlib import Path

from core.annotation.list_tier_names import ListTierNames
from core.import_metadata.information_sources_file import stored_file_name
from core.import_metadata.read_metadata_csv import ReadMetadataCsv
from core.import_words.entity.word_table import (
    WordImportResult,
    WordMatch,
    WordSource,
)
from core.import_words.import_words import ImportWords
from core.import_words.match_words import MatchWords
from core.import_words.save_unmatched_words import SaveUnmatchedWords
from core.import_words.word_source_file import SaveWordSource
from phonlab_project.readers.metadata_table import MetadataTable
from res.constants import WORD_EXAMPLE_UNMATCHED
from ui.base.view_model import ViewModel
from ui.word_import.state.word_import_state import WordColumnState, WordImportState

# tiers with the words in them are usually called this
WORD_TIER_NAMES = ("word", "words")


class WordImportViewModel(ViewModel):
    """Adds a table with a row for each word, from a CSV file, to the project
    database as its word table, and says how many of the words of a tier of the
    annotations the table has. The first column has the words."""

    def __init__(
        self,
        dir_path: str,
        csv_path: str,
        read_csv: ReadMetadataCsv,
        match_words: MatchWords,
        import_words: ImportWords,
        list_tier_names: ListTierNames,
        save_unmatched_words: SaveUnmatchedWords,
        save_source: SaveWordSource,
    ):
        super().__init__()
        self.dir_path = dir_path
        self.csv_path = csv_path
        self.read_csv = read_csv
        self.match_words = match_words
        self.import_words_use_case = import_words
        self.list_tier_names = list_tier_names
        self.save_unmatched_words = save_unmatched_words
        self.save_source = save_source

        self.table = MetadataTable()
        self.tiers: list[str] = []
        self.tier = ""
        self.match = WordMatch("")

    def prepare(self):
        """Reads the file. Raises ValueError if it cannot be used, or the project has
        no tier to match the words to."""
        self.table = self.read_csv(self.csv_path)
        self.tiers = self.list_tier_names()
        if not self.tiers:
            raise ValueError(
                self.tr(
                    "The project database has no annotation. Read the "
                    "annotation files first, then add the words."
                )
            )
        self.tier = next(
            (t for t in self.tiers if t.casefold() in WORD_TIER_NAMES), self.tiers[0]
        )
        self._rematch()
        self.emit_state()

    def set_tier(self, tier: str):
        """Match the words of the table with the labels of this tier"""
        self.tier = tier
        self._rematch()
        self.emit_state()

    def _rematch(self):
        self.match = self.match_words(self.table, self.tier)

    # ------------------------------ result ------------------------------

    @property
    def can_import(self) -> bool:
        return self.match.n_rows > 0

    def import_words(self) -> WordImportResult:
        """Makes the word table of the project database, and remembers the file in the
        project file, so a rebuilt database gets the same table again"""
        plans = self.import_words_use_case.plan_columns(self.table)
        result = self.import_words_use_case(self.table, plans)
        self.save_source(
            self.dir_path,
            WordSource(
                stored_file_name(self.dir_path, self.csv_path),
                self.tier,
                {plan.source: plan.name for plan in plans},
            ),
        )
        return result

    def save_unmatched(self, path: str) -> int:
        """Writes the words of the tier that the table lacks to a CSV file"""
        return self.save_unmatched_words(path, self.match.unmatched)

    # ------------------------------ state ------------------------------

    def emit_state(self):
        self.state_changed.emit(self.to_state())

    def to_state(self) -> WordImportState:
        match = self.match
        plans = {
            plan.source: plan
            for plan in self.import_words_use_case.plan_columns(self.table)
        }
        first_row = self.table.rows[0] if self.table.rows else []
        most_often = sorted(match.unmatched, key=lambda w: (-match.unmatched[w], w))
        return WordImportState(
            file_name=Path(self.csv_path).name,
            key_column=self.table.headers[0] if self.table.headers else "",
            tier=self.tier,
            tiers=list(self.tiers),
            n_rows=match.n_rows,
            n_duplicates=match.n_duplicates,
            n_words=match.n_words,
            n_found=match.n_found,
            n_unmatched=match.n_unmatched,
            n_extra=match.n_extra,
            unmatched_examples=most_often[:WORD_EXAMPLE_UNMATCHED],
            columns=[
                WordColumnState(
                    source=header,
                    name=plans[header].name,
                    sql_type=plans[header].sql_type,
                    example=first_row[index] if index < len(first_row) else "",
                )
                for index, header in enumerate(self.table.headers)
                if header in plans
            ],
            can_import=self.can_import,
        )
