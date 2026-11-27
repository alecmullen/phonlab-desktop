from pathlib import Path

from core.import_metadata.entity.information_source import InformationSource
from core.import_metadata.import_metadata import ImportMetadata
from core.import_metadata.information_sources_file import (
    SaveInformationSource,
    stored_file_name,
)
from core.import_metadata.match_metadata import MatchMetadata
from core.import_metadata.read_metadata_csv import ReadMetadataCsv
from phonlab_project.metadata import MetadataTarget
from phonlab_project.readers.metadata_table import (
    MetadataColumnPlan,
    MetadataImportResult,
    MetadataMatch,
    MetadataTable,
)
from ui.base.view_model import ViewModel
from ui.metadata_import.state.metadata_import_state import (
    MetadataColumnState,
    MetadataImportState,
)

# headers that usually hold the names of what a row is about
KEY_HEADER_HINTS = {
    MetadataTarget.TALKER: ("talker", "speaker", "subject", "participant", "id"),
    MetadataTarget.RECORDING: (
        "recording",
        "file",
        "filename",
        "file_name",
        "stem",
        "audio",
        "wav",
    ),
}


class MetadataImportViewModel(ViewModel):
    """Adds the columns of a CSV file, one row per talker or one row per recording,
    to the project database. It finds the column that names the talkers or
    recordings by trying them all."""

    def __init__(
        self,
        dir_path: str,
        csv_path: str,
        read_csv: ReadMetadataCsv,
        match_metadata: MatchMetadata,
        import_metadata: ImportMetadata,
        save_source: SaveInformationSource,
        fixed_target: MetadataTarget | None = None,
    ):
        super().__init__()
        # when it is set the rows are about this, and the user is not asked
        self.fixed_target = fixed_target
        self.dir_path = dir_path
        self.save_source = save_source
        self.csv_path = csv_path
        self.read_csv = read_csv
        self.match_metadata = match_metadata
        self.import_metadata = import_metadata

        self.table = MetadataTable()
        self.target = MetadataTarget.TALKER
        self.key_column = ""
        self.match: MetadataMatch | None = None
        self.names: dict[str, str] = {}
        self.selected: set[str] = set()

    def prepare(self):
        """Reads the file. Raises ValueError if it cannot be used."""
        self.table = self.read_csv(self.csv_path)

        best: tuple[tuple[int, int], MetadataTarget, str] | None = None
        for target in [self.fixed_target] if self.fixed_target else MetadataTarget:
            key = self._best_key_column(target)
            score = self._score(target, key)
            if best is None or score > best[0]:
                best = (score, target, key)
        assert best is not None
        _, self.target, self.key_column = best

        self.names = {header: header for header in self.table.headers}
        self._select_all_but_key()
        self._rematch()
        self.emit_state()

    # ------------------------------ edits ------------------------------

    def set_target(self, target: str):
        self.target = MetadataTarget(target)
        self.key_column = self._best_key_column(self.target)
        self._select_all_but_key()
        self._rematch()
        self.emit_state()

    def set_key_column(self, header: str):
        self.key_column = header
        self._select_all_but_key()
        self._rematch()
        self.emit_state()

    def set_column_selected(self, source: str, selected: bool):
        if selected:
            self.selected.add(source)
        else:
            self.selected.discard(source)
        self.emit_state()

    def set_column_name(self, source: str, name: str):
        self.names[source] = name.strip() or source
        self.emit_state()

    def _select_all_but_key(self):
        self.selected = {h for h in self.table.headers if h != self.key_column}

    def _best_key_column(self, target: MetadataTarget) -> str:
        return max(self.table.headers, key=lambda h: self._score(target, h))

    def _score(self, target: MetadataTarget, header: str) -> tuple[int, int]:
        """How many rows the column matches, and whether its name is a usual one"""
        matched = self.match_metadata(self.table, target, header).n_matched
        hinted = header.casefold() in KEY_HEADER_HINTS[target]
        return (matched, int(hinted))

    def _rematch(self):
        self.match = self.match_metadata(self.table, self.target, self.key_column)

    # ------------------------------ result ------------------------------

    def _plans(self) -> list[MetadataColumnPlan]:
        wanted = {
            header: self.names.get(header, header)
            for header in self.table.headers
            if header in self.selected and header != self.key_column
        }
        return self.import_metadata.plan_columns(self.table, self.target, wanted)

    @property
    def can_import(self) -> bool:
        return (
            self.match is not None
            and self.match.n_matched > 0
            and len(self._plans()) > 0
        )

    def import_information(self) -> MetadataImportResult:
        """Adds the columns to the project database, and remembers the file and what
        was chosen in the project file, so a rebuilt database can get the same
        information again"""
        if self.match is None or self.match.n_matched == 0:
            raise ValueError(
                "No row of the file names a talker or recording in the project"
            )

        plans = self._plans()
        result = self.import_metadata(self.table, self.match, plans)
        self.save_source(
            self.dir_path,
            InformationSource(
                file=stored_file_name(self.dir_path, self.csv_path),
                target=self.target,
                key_column=self.key_column,
                columns={
                    plan.source: self.names.get(plan.source, plan.source)
                    for plan in plans
                },
            ),
        )
        return result

    # ------------------------------ state ------------------------------

    def emit_state(self):
        self.state_changed.emit(self.to_state())

    def to_state(self) -> MetadataImportState:
        match = self.match
        plans = {plan.source: plan for plan in self._plans()}
        first_row = self.table.rows[0] if self.table.rows else []

        columns = []
        for index, header in enumerate(self.table.headers):
            if header == self.key_column:
                continue
            plan = plans.get(header)
            columns.append(
                MetadataColumnState(
                    source=header,
                    name=plan.name if plan else self.names.get(header, header),
                    sql_type=plan.sql_type.value if plan else "",
                    example=first_row[index] if index < len(first_row) else "",
                    selected=header in self.selected,
                )
            )

        return MetadataImportState(
            file_name=Path(self.csv_path).name,
            target=self.target.value,
            target_locked=self.fixed_target is not None,
            key_column=self.key_column,
            key_columns=list(self.table.headers),
            n_rows=match.n_rows if match else 0,
            n_matched=match.n_matched if match else 0,
            n_targets=match.n_targets if match else 0,
            n_unmatched_targets=match.n_unmatched_targets if match else 0,
            n_duplicates=match.n_duplicates if match else 0,
            strategy=match.strategy if match else "",
            unmatched_examples=list(match.unmatched_values) if match else [],
            unmatched_target_examples=list(match.unmatched_targets) if match else [],
            columns=columns,
            can_import=self.can_import,
        )
