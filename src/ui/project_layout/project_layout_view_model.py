from dataclasses import replace
from pathlib import Path

from core.project_layout.infer_layout import InferLayout
from core.project_layout.project_layout_file import (
    LoadProjectLayout,
    SaveProjectLayout,
)
from core.project_layout.resolve_recordings import ResolveRecordings
from core.project_layout.scan_project_tree import ScanProjectTree
from core.project_layout.suggest_talker_names import SuggestTalkerNames
from core.read_tiers.preview_annotation_table import PreviewAnnotationTable
from phonlab_project.constants import (
    ANNOTATION_FORMATS,
    DATA_FILE_MIN_COVERAGE,
    TALKER_FIELD_NAMES,
)
from phonlab_project.layout.import_report import (
    DataFileCandidate,
    FolderSources,
    LayoutSuggestion,
    ResolvedProject,
)
from phonlab_project.layout.project_layout import (
    ChannelRole,
    DataFileKind,
    DataFileRole,
    FolderLevel,
    ProjectLayout,
)
from phonlab_project.layout.project_scan import ProjectScan
from phonlab_project.layout.template_variables import (
    layout_variables,
    talker_template_problem,
    without_unusable_templates,
)
from phonlab_project.readers.table_format import ColumnRole, TableFormat, TimeUnit
from res.constants import PROJECT_PREVIEW_ROWS, PROJECT_REPORT_EXAMPLES
from ui.base.view_model import ViewModel
from ui.project_layout.state.annotation_table_state import AnnotationTableState
from ui.project_layout.state.project_layout_state import (
    ChannelCandidateState,
    ChannelRoleState,
    DataFileRoleState,
    FolderChoiceState,
    FolderLevelState,
    ProjectLayoutState,
)


class ProjectLayoutViewModel(ViewModel):
    """Works out how a project directory is organized and lets the user correct it.
    The layout is kept in the project's phonlab.toml, so the project is read the same
    way next time without questions."""

    def __init__(
        self,
        dir_path: str,
        scan_project_tree: ScanProjectTree,
        infer_layout: InferLayout,
        resolve_recordings: ResolveRecordings,
        load_layout: LoadProjectLayout,
        save_layout: SaveProjectLayout,
        suggest_talker_names: SuggestTalkerNames,
        preview_annotation_table: PreviewAnnotationTable,
    ):
        super().__init__()
        self.dir_path = dir_path
        self.scan_project_tree = scan_project_tree
        self.infer_layout = infer_layout
        self.resolve_recordings = resolve_recordings
        self.load_layout = load_layout
        self.save_layout = save_layout
        self.suggest_talker_names = suggest_talker_names
        self.preview_annotation_table = preview_annotation_table

        self.scan: ProjectScan | None = None
        self.suggestion = LayoutSuggestion(ProjectLayout())
        self.layout = ProjectLayout()
        self.has_saved_layout = False
        self.candidates: list[DataFileCandidate] = []
        self.selected_roles: list[bool] = []
        self.resolved = ResolvedProject()
        self.template_error = ""
        self.talker_template_error = ""
        # the channels the user may combine into recordings, with talker names
        self.channel_roles: tuple[ChannelRole, ...] = ()
        self.talker_names: list[str] = []

    # ------------------------------ setup ------------------------------

    def prepare(self):
        """Scans the project and takes the saved layout, or else the suggested one"""
        self.scan = self.scan_project_tree(self.dir_path)

        saved = self.load_layout(self.dir_path)
        self.has_saved_layout = saved is not None
        self.suggestion = self.infer_layout(
            self.scan, saved.channels if saved is not None else None
        )
        candidate = self.suggestion.channel_candidate
        if saved is not None and saved.channels:
            self.channel_roles = saved.channels
        elif candidate is not None:
            self.channel_roles = candidate.roles
        self.candidates = list(self.suggestion.data_file_candidates)

        if saved is None:
            self.layout = self.suggestion.layout
            self.selected_roles = [
                c.role in self.layout.data_files for c in self.candidates
            ]
        else:
            self.layout = saved
            self._adopt_saved_roles(saved)

        self._resolve()
        self._refresh_talker_names()
        self.emit_state()

    def _adopt_saved_roles(self, saved: ProjectLayout):
        """Marks the candidates the saved layout uses (with its names for them), and
        keeps saved kinds of files that no longer turn up in the project"""
        saved_by_key = {role.key: role for role in saved.data_files}
        candidates: list[DataFileCandidate] = []
        selected: list[bool] = []
        for candidate in self.candidates:
            role = saved_by_key.pop(candidate.role.key, None)
            if role is None:
                candidates.append(candidate)
                selected.append(False)
            else:
                candidates.append(replace(candidate, role=role))
                selected.append(True)
        for role in saved_by_key.values():
            candidates.append(DataFileCandidate(role, 0, 0.0))
            selected.append(True)
        self.candidates, self.selected_roles = candidates, selected
        self.layout = replace(saved, data_files=self._selected_roles())

    @property
    def needs_review(self) -> bool:
        """Whether the user has anything to decide. A project that is just audio
        files with matching annotations next to them is imported without asking."""
        report = self.resolved.report
        if self.has_saved_layout:
            return report.n_recordings == 0 or len(report.template_mismatches) > 0
        return (
            len(self.suggestion.levels) > 0
            or len(self.candidates) > 0
            or self.suggestion.channel_candidate is not None
            or len(report.unpaired_audio) > 0
            or len(report.unpaired_annotations) > 0
            or len(report.duplicate_audio) > 0
            or self._annotation_sources().overlapping
            or report.n_recordings == 0
        )

    # ------------------------------ edits ------------------------------

    def set_level_field(self, depth: int, name: str):
        levels = {level.depth: level for level in self.layout.levels}
        levels[depth] = replace(
            levels.get(depth, FolderLevel(depth)), field=name.strip()
        )
        self._set_layout(
            replace(
                self.layout,
                levels=tuple(sorted(levels.values(), key=lambda l: l.depth)),
            )
        )

    def set_level_template(self, depth: int, template: str):
        levels = {level.depth: level for level in self.layout.levels}
        levels[depth] = replace(
            levels.get(depth, FolderLevel(depth)), template=template.strip()
        )
        self._set_layout(
            replace(
                self.layout,
                levels=tuple(sorted(levels.values(), key=lambda l: l.depth)),
            )
        )

    def set_talker_template(self, template: str):
        self._set_layout(replace(self.layout, talker_template=template.strip()))

    def set_filename_template(self, template: str):
        self._set_layout(replace(self.layout, filename_template=template.strip()))

    def set_include_unpaired_audio(self, include: bool):
        self._set_layout(replace(self.layout, include_unpaired_audio=include))

    def set_annotation_ext(self, ext: str):
        ext = ext.casefold()
        sources = self.suggestion.annotation_sources.get(ext, FolderSources())
        self.layout = replace(
            self.layout, annotation_ext=ext or None, annotation_dir=sources.default
        )
        self._resolve()
        self._refresh_talker_names()
        self.emit_state()

    def set_annotation_dir(self, folder: str):
        """Reads annotations only from `folder` (relative to the project); empty reads
        them from anywhere"""
        self.layout = replace(self.layout, annotation_dir=folder)
        self._resolve()
        self._refresh_talker_names()
        self.emit_state()

    def _annotation_sources(self) -> FolderSources:
        return self.suggestion.annotation_sources.get(
            self.layout.annotation_ext or "", FolderSources()
        )

    def set_channels_enabled(self, enabled: bool):
        """Whether audio files that differ by a channel suffix are the channels of one
        recording. The other things found in the project depend on the answer, so the
        project is looked at again."""
        if self.scan is None or not self.channel_roles:
            return
        channels = self.channel_roles if enabled else ()
        previous = {
            candidate.role.key: (candidate.role, selected)
            for candidate, selected in zip(self.candidates, self.selected_roles)
        }
        self.suggestion = self.infer_layout(self.scan, channels)

        self.candidates, self.selected_roles = [], []
        for candidate in self.suggestion.data_file_candidates:
            role, selected = previous.pop(
                candidate.role.key,
                (candidate.role, candidate.coverage >= DATA_FILE_MIN_COVERAGE),
            )
            self.candidates.append(replace(candidate, role=role))
            self.selected_roles.append(selected)
        for role, selected in previous.values():
            if selected:
                self.candidates.append(DataFileCandidate(role, 0, 0.0))
                self.selected_roles.append(True)

        self.layout = replace(
            self.layout,
            channels=channels,
            annotation_ext=self.layout.annotation_ext
            or self.suggestion.layout.annotation_ext,
            data_files=self._selected_roles(),
        )
        self._resolve()
        self._refresh_talker_names()
        self.emit_state()

    def set_channel_talker(self, index: int, talker: str):
        roles = list(self.channel_roles)
        roles[index] = replace(roles[index], talker=talker.strip())
        self.channel_roles = tuple(roles)
        if self.layout.channels:
            self._set_layout(replace(self.layout, channels=self.channel_roles))

    def _refresh_talker_names(self):
        """Names for talkers found in the tiers of an annotation file. When there is
        one name for each channel and none is given yet they are used in order."""
        self.talker_names = []
        if not self.layout.channels or self.layout.annotation_ext is None:
            return
        annotated = next(
            (r for r in self.resolved.recordings if r.annotation_file), None
        )
        if annotated is None or annotated.annotation_file is None:
            return
        self.talker_names = self.suggest_talker_names(
            self.dir_path, annotated.annotation_file
        )
        if not any(role.talker for role in self.channel_roles) and len(
            self.talker_names
        ) == len(self.channel_roles):
            self.channel_roles = tuple(
                replace(role, talker=name)
                for role, name in zip(self.channel_roles, self.talker_names)
            )
            # the talkers are on the channels, so a folder level guessed to hold the
            # talker (it may be a folder for the pair) is not offered as one
            levels = tuple(
                replace(level, field="")
                if level.field.casefold() in TALKER_FIELD_NAMES
                else level
                for level in self.layout.levels
            )
            self.layout = replace(
                self.layout, channels=self.channel_roles, levels=levels
            )
            self._resolve()

    def set_role_selected(self, index: int, selected: bool):
        self.selected_roles[index] = selected
        self._set_layout(replace(self.layout, data_files=self._selected_roles()))

    def set_role_name(self, index: int, name: str):
        role = self.candidates[index].role
        name = name.strip() or role.name
        self.candidates[index] = replace(
            self.candidates[index], role=replace(role, name=name)
        )
        self._set_layout(replace(self.layout, data_files=self._selected_roles()))

    def set_role_kind(self, index: int, kind: str):
        """What the files of a kind are for: "annotation", "time_series" or "other" """
        role = self.candidates[index].role
        self.candidates[index] = replace(
            self.candidates[index], role=replace(role, kind=DataFileKind(kind))
        )
        self._set_layout(replace(self.layout, data_files=self._selected_roles()))

    def set_role_tier(self, index: int, tier: str):
        """The name of the tier that files of an annotation kind hold"""
        role = self.candidates[index].role
        self.candidates[index] = replace(
            self.candidates[index], role=replace(role, tier=tier.strip())
        )
        self._set_layout(replace(self.layout, data_files=self._selected_roles()))

    def annotation_table(
        self,
        index: int,
        delimiter: str | None = None,
        skip: int | None = None,
        unit: str | None = None,
        columns: list[str] | None = None,
    ) -> AnnotationTableState:
        """How a file of a kind of extra file reads as a table of labelled intervals,
        for the user to check: the first such file in the project, as the layout has it,
        with the delimiter, number of lines to skip and unit of time given taking the
        place of what the layout (or else the file) says. With `columns` (the roles the
        user gave them) as well, the format is just that, to be checked."""
        role = self.candidates[index].role
        sample = next(
            (
                (r.tier_files[role.tier_name], r.audio_file)
                for r in self.resolved.recordings
                if role.tier_name in r.tier_files
            ),
            None,
        )
        if sample is None:
            return AnnotationTableState(
                problem=self.tr("There is no file of this kind to look at.")
            )

        file, audio = sample
        root = Path(self.dir_path)
        try:
            preview = self.preview_annotation_table(
                str(root / file),
                str(root / audio) if audio else None,
                TableFormat(
                    delimiter or "",
                    skip or 0,
                    tuple(ColumnRole(column) for column in columns),
                    TimeUnit(unit or "auto"),
                )
                if columns
                else role.table,
                delimiter,
                skip,
                TimeUnit(unit) if unit else None,
            )
        except (ValueError, OSError) as err:
            return AnnotationTableState(file_name=Path(file).name, problem=str(err))
        label = (
            preview.format.columns.index(ColumnRole.LABEL)
            if ColumnRole.LABEL in preview.format.columns
            else None
        )
        # the tier is called what the user said, else what the file calls the column
        # of labels, else the name of the kind of file
        named = preview.names[label] if label is not None and preview.names else ""
        return AnnotationTableState(
            file_name=Path(file).name,
            tier=role.tier or named or role.name,
            delimiter=preview.format.delimiter,
            skip=preview.format.skip,
            unit=preview.format.unit.value,
            unit_used=preview.unit.value,
            columns=[column.value for column in preview.format.columns],
            names=list(preview.names),
            rows=preview.rows,
            n_rows=preview.n_rows,
            problem=preview.problem,
        )

    def set_role_table(
        self,
        index: int,
        delimiter: str,
        skip: int,
        columns: list[str],
        unit: str,
        tier: str | None = None,
    ):
        """How files of a kind of extra file are read as tables of labelled intervals,
        and the name of the tier they hold if it is given"""
        role = self.candidates[index].role
        table = TableFormat(
            delimiter,
            skip,
            tuple(ColumnRole(column) for column in columns),
            TimeUnit(unit),
        )
        self.candidates[index] = replace(
            self.candidates[index],
            role=replace(
                role, table=table, tier=role.tier if tier is None else tier.strip()
            ),
        )
        self._set_layout(replace(self.layout, data_files=self._selected_roles()))

    def _selected_roles(self) -> tuple[DataFileRole, ...]:
        roles: list[DataFileRole] = []
        used: set[str] = set()
        for candidate, selected in zip(self.candidates, self.selected_roles):
            if not selected:
                continue
            role = candidate.role
            name, number = role.name, 1
            while name in used:
                number += 1
                name = f"{role.name}_{number}"
            used.add(name)
            roles.append(replace(role, name=name))
        return tuple(roles)

    def _set_layout(self, layout: ProjectLayout):
        self.layout = layout
        self._resolve()
        self.emit_state()

    def _resolve(self):
        if self.scan is None:
            return
        layout, self.template_error = without_unusable_templates(self.layout)
        layout = replace(layout, talker_template=self.layout.talker_template)
        self.talker_template_error = talker_template_problem(layout)
        if self.talker_template_error:
            layout = replace(layout, talker_template="")
        self.resolved = self.resolve_recordings(self.scan, layout)

    # ------------------------------ result ------------------------------

    @property
    def can_import(self) -> bool:
        return (
            self.template_error == ""
            and self.talker_template_error == ""
            and self.resolved.report.n_recordings > 0
        )

    def save_project_layout(self):
        """Saves the layout in the project's phonlab.toml. The project's files are
        then read the way it says when the project database is built or updated."""
        if self.template_error or self.talker_template_error:
            raise ValueError(self.template_error or self.talker_template_error)

        self.save_layout(self.dir_path, self.layout)
        self.has_saved_layout = True

    # ------------------------------ state ------------------------------

    def emit_state(self):
        self.state_changed.emit(self.to_state())

    def to_state(self) -> ProjectLayoutState:
        report = self.resolved.report
        fields = {level.depth: level.field for level in self.layout.levels}
        templates = {level.depth: level.template for level in self.layout.levels}

        levels = [
            FolderLevelState(
                summary.depth,
                summary.n_values,
                ", ".join(summary.examples)
                + (" …" if summary.n_values > len(summary.examples) else ""),
                fields.get(summary.depth, ""),
                self._level_note(summary.name_prefix_share),
                templates.get(summary.depth, ""),
            )
            for summary in self.suggestion.levels
        ]
        roles = [
            DataFileRoleState(
                candidate.role.name,
                f"*{candidate.role.suffix}{candidate.role.ext}",
                candidate.n_files,
                round(candidate.coverage * 100),
                selected,
                candidate.role.kind.value,
                candidate.role.tier,
            )
            for candidate, selected in zip(self.candidates, self.selected_roles)
        ]

        candidate = self.suggestion.channel_candidate
        channel_candidate = None
        if candidate is not None:
            channel_candidate = ChannelCandidateState(
                candidate.n_groups,
                "; ".join(candidate.examples),
                self._channel_evidence(candidate.looks_like_channels),
            )
        channels = [
            ChannelRoleState(role.label, role.suffix, role.talker)
            for role in self.channel_roles
        ]

        headers, rows = self._preview()
        return ProjectLayoutState(
            n_audio=report.n_audio,
            n_audio_files=report.n_audio_files,
            n_recordings=report.n_recordings,
            n_annotated=report.n_annotated,
            n_unpaired_audio=len(report.unpaired_audio),
            n_unpaired_annotations=len(report.unpaired_annotations),
            unpaired_audio_examples=report.unpaired_audio[:PROJECT_REPORT_EXAMPLES],
            unpaired_annotation_examples=report.unpaired_annotations[
                :PROJECT_REPORT_EXAMPLES
            ],
            n_duplicate_audio=len(report.duplicate_audio),
            duplicate_audio_examples=report.duplicate_audio[:PROJECT_REPORT_EXAMPLES],
            annotation_ext=self.layout.annotation_ext or "",
            annotation_exts=[
                ext
                for ext in ANNOTATION_FORMATS
                if self.suggestion.annotation_sources[ext].n_paired > 0
                or ext == self.layout.annotation_ext
            ],
            annotation_dir=self.layout.annotation_dir,
            annotation_folders=[
                FolderChoiceState(f.folder, f.n_files)
                for f in self._annotation_sources().folders
            ],
            annotation_folders_overlap=self._annotation_sources().overlapping,
            include_unpaired_audio=self.layout.include_unpaired_audio,
            channel_candidate=channel_candidate,
            channels_enabled=len(self.layout.channels) > 0,
            channels=channels,
            talker_names=list(self.talker_names),
            levels=levels,
            roles=roles,
            filename_template=self.layout.filename_template,
            talker_template=self.layout.talker_template,
            talker_template_error=self.talker_template_error,
            variables=layout_variables(self.layout),
            template_error=self.template_error,
            n_template_mismatches=len(report.template_mismatches),
            template_mismatch_examples=report.template_mismatches[
                :PROJECT_REPORT_EXAMPLES
            ],
            preview_headers=headers,
            preview_rows=rows,
            can_import=self.can_import,
        )

    def _preview(self) -> tuple[list[str], list[list[str]]]:
        # a sample that shows the recordings that have annotations first, so that the
        # few that do are not hidden among many that do not
        ordered = sorted(
            self.resolved.recordings, key=lambda r: r.annotation_file is None
        )
        recordings = ordered[:PROJECT_PREVIEW_ROWS]
        field_names = sorted({name for r in recordings for name in r.fields})
        role_names = [role.name for role in self.layout.data_files]

        headers = [
            "Recording",
            "Talkers",
            *field_names,
            "Audio",
            "Annotation",
            *role_names,
        ]
        rows = [
            [
                recording.file_stem,
                ", ".join(recording.talkers),
                *[recording.fields.get(name, "") for name in field_names],
                ", ".join(recording.channel_files.values())
                if recording.channel_files
                else recording.audio_file or "—",
                recording.annotation_file or "—",
                *[
                    recording.data_files.get(role.name)
                    or recording.tier_files.get(role.tier_name)
                    or "—"
                    for role in self.layout.data_files
                ],
            ]
            for recording in recordings
        ]
        return headers, rows

    def _level_note(self, name_prefix_share: float) -> str:
        if name_prefix_share >= 0.9:
            return self.tr("file names start with the folder name")
        return ""

    def _channel_evidence(self, looks_like_channels: bool | None) -> str:
        if looks_like_channels is True:
            return self.tr(
                "The files are mono and equally long, like channels of one recording."
            )
        return self.tr("The files could not be read to check.")
