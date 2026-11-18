from core.base.use_case_sync import UseCaseSync
from core.import_metadata.entity.information_source import AppliedInformation
from core.import_metadata.import_metadata import ImportMetadata
from core.import_metadata.information_sources_file import (
    LoadInformationSources,
    resolved_file_name,
)
from core.import_metadata.match_metadata import MatchMetadata
from core.import_metadata.read_metadata_csv import ReadMetadataCsv
from core.import_words.import_words import ImportWords
from core.import_words.word_source_file import LoadWordSource


class ApplyInformationSources(UseCaseSync[AppliedInformation]):
    """Adds the information of the project's saved CSV files to the project database
    again, for example after the database was rebuilt. Each file is read as it is
    now, with the key column and columns chosen when it was first added, and so is the
    table of words, if the project has one. A file that
    is missing or no longer fits is reported, and the others are still added."""

    def __init__(
        self,
        load_sources: LoadInformationSources,
        read_csv: ReadMetadataCsv,
        match_metadata: MatchMetadata,
        import_metadata: ImportMetadata,
        load_word_source: LoadWordSource | None = None,
        import_words: ImportWords | None = None,
    ):
        self.load_sources = load_sources
        self.read_csv = read_csv
        self.match_metadata = match_metadata
        self.import_metadata = import_metadata
        self.load_word_source = load_word_source
        self.import_words = import_words

    def __call__(self, dir_path: str) -> AppliedInformation:
        applied: list[str] = []
        failed: list[str] = []
        for source in self.load_sources(dir_path):
            try:
                table = self.read_csv(resolved_file_name(dir_path, source.file))
                if source.key_column not in table.headers:
                    raise ValueError(f"No column called {source.key_column}")
                wanted = {
                    header: name
                    for header, name in source.columns.items()
                    if header in table.headers
                }
                match = self.match_metadata(table, source.target, source.key_column)
                if match.n_matched == 0:
                    raise ValueError("No row names a talker or recording")
                plans = self.import_metadata.plan_columns(table, source.target, wanted)
                self.import_metadata(table, match, plans)
                applied.append(source.file)
            except (OSError, ValueError):
                failed.append(source.file)

        word_source = self.load_word_source(dir_path) if self.load_word_source else None
        if word_source is not None and self.import_words is not None:
            try:
                table = self.read_csv(resolved_file_name(dir_path, word_source.file))
                wanted = {
                    header: name
                    for header, name in word_source.columns.items()
                    if header in table.headers[1:]
                }
                self.import_words(table, self.import_words.plan_columns(table, wanted))
                applied.append(word_source.file)
            except (OSError, ValueError):
                failed.append(word_source.file)
        return AppliedInformation(applied, failed)
