from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from res.constants import ANNOTATION_FORMATS
from ui.project_layout.component.annotation_table_dialog import AnnotationTableDialog
from ui.project_layout.project_layout_view_model import ProjectLayoutViewModel
from ui.project_layout.state.project_layout_state import (
    FolderChoiceState,
    ProjectLayoutState,
)

ANNOTATION_KIND = "annotation"  # the kind of file that holds a tier of an annotation

TEMPLATE_HELP = (
    "{name} is a field; {name:3} takes exactly 3 characters; {name:d} digits; "
    "{name:a} letters; {*} skips characters; (ignore) allows anything, or nothing, "
    "that is not kept (anywhere in the name). Start with re: to use a regular "
    "expression with named groups. A field called talker or speaker names the talker."
)


class ProjectLayoutDialog(QDialog):
    """Shows how the project directory looks to Phonlab (what was paired with
    what, what was left over) and lets the user say what the folders and file
    names mean before the recordings are recorded in the project database."""

    @staticmethod
    def review_layout(
        view_model: ProjectLayoutViewModel,
        parent: QWidget | None = None,
        force_review: bool = False,
    ) -> bool:
        """Settles how the project is organized, asking the user first when there is
        something to decide (or when `force_review` is set), and saves the layout.
        Returns False if the user cancelled."""
        view_model.prepare()

        if not force_review and not view_model.needs_review:
            view_model.save_project_layout()
            return True

        dialog = ProjectLayoutDialog(view_model, parent)
        return dialog.exec() == QDialog.DialogCode.Accepted

    def __init__(
        self, view_model: ProjectLayoutViewModel, parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.view_model = view_model
        self.state = ProjectLayoutState()
        self._built = False

        self.setWindowTitle(self.tr("Project Layout"))
        self.resize(940, 780)

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        scroll.setWidget(content)
        outer.addWidget(scroll)

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.content_layout.addWidget(self.summary_label)

        self._build_annotation_group()
        self._build_unpaired_group()
        self.channels_group = QGroupBox(self.tr("Channels in separate files"))
        self.channels_layout = QVBoxLayout(self.channels_group)
        self.content_layout.addWidget(self.channels_group)
        self.talker_combos: list[QComboBox] = []
        # for each kind of extra file: its kind list, tier name box and Columns button
        self.role_widgets: list[tuple[QComboBox, QLineEdit, QPushButton]] = []
        self.levels_group = QGroupBox(self.tr("Folders"))
        self.levels_layout = QVBoxLayout(self.levels_group)
        self.content_layout.addWidget(self.levels_group)
        self._build_filename_group()
        self.roles_group = QGroupBox(self.tr("Other files for each recording"))
        self.roles_layout = QVBoxLayout(self.roles_group)
        self.content_layout.addWidget(self.roles_group)
        self._build_preview_group()
        self.content_layout.addStretch(1)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.import_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if self.import_button is not None:
            self.import_button.setText(self.tr("Use This Layout"))
        self.button_box.accepted.connect(self.accept_layout)
        self.button_box.rejected.connect(self.reject)
        outer.addWidget(self.button_box)

        self.view_model.subscribe(self.on_state)
        self.view_model.emit_state()

    # ------------------------------ building ------------------------------

    def _build_annotation_group(self):
        group = QGroupBox(self.tr("Annotations"))
        column = QVBoxLayout(group)
        layout = QHBoxLayout()
        layout.addWidget(QLabel(self.tr("Annotation files:")))
        self.annotation_combo = QComboBox()
        self.annotation_combo.currentIndexChanged.connect(self.on_annotation_changed)
        layout.addWidget(self.annotation_combo)
        self.annotation_note = QLabel()
        layout.addWidget(self.annotation_note, 1)
        column.addLayout(layout)

        self.folder_widget = QWidget()
        folder_layout = QHBoxLayout(self.folder_widget)
        folder_layout.setContentsMargins(0, 0, 0, 0)
        folder_layout.addWidget(QLabel(self.tr("Read them from:")))
        self.folder_combo = QComboBox()
        self.folder_combo.currentIndexChanged.connect(self.on_annotation_folder_changed)
        folder_layout.addWidget(self.folder_combo)
        self.folder_note = QLabel()
        self.folder_note.setWordWrap(True)
        folder_layout.addWidget(self.folder_note, 1)
        column.addWidget(self.folder_widget)
        self.content_layout.addWidget(group)

    def _build_unpaired_group(self):
        group = QGroupBox(self.tr("Files without a partner"))
        layout = QVBoxLayout(group)
        self.unpaired_audio_label = QLabel()
        self.unpaired_audio_label.setWordWrap(True)
        self.unpaired_audio_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.unpaired_audio_label)
        self.leave_out_check = QCheckBox(
            self.tr("Leave out audio files that have no annotation")
        )
        self.leave_out_check.toggled.connect(self.on_leave_out_toggled)
        layout.addWidget(self.leave_out_check)
        self.unpaired_annotation_label = QLabel()
        self.unpaired_annotation_label.setWordWrap(True)
        self.unpaired_annotation_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.unpaired_annotation_label)
        self.duplicate_audio_label = QLabel()
        self.duplicate_audio_label.setWordWrap(True)
        self.duplicate_audio_label.setStyleSheet("color: #b36b00;")
        self.duplicate_audio_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.duplicate_audio_label)
        self.content_layout.addWidget(group)

    def _build_filename_group(self):
        group = QGroupBox(self.tr("File names"))
        layout = QVBoxLayout(group)
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Name template:")))
        self.template_edit = QLineEdit()
        self.template_edit.setPlaceholderText(
            self.tr("e.g. {talker:3}{session:2}(ignore)  (leave empty to skip)")
        )
        self.template_edit.textEdited.connect(self.view_model.set_filename_template)
        row.addWidget(self.template_edit, 1)
        layout.addLayout(row)

        help_label = QLabel(self.tr(TEMPLATE_HELP))
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        self.template_status = QLabel()
        self.template_status.setWordWrap(True)
        layout.addWidget(self.template_status)
        self.content_layout.addWidget(group)

    def _build_preview_group(self):
        group = QGroupBox(self.tr("Preview of what will be recorded"))
        layout = QVBoxLayout(group)
        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.setMinimumHeight(220)
        layout.addWidget(self.preview_table)
        self.content_layout.addWidget(group)

    def _build_channels(self, state: ProjectLayoutState):
        candidate = state.channel_candidate
        if candidate is None:
            self.channels_group.hide()
            return

        intro = QLabel(
            self.tr(
                "{} sets of audio files differ only by an ending, for example: {}"
            ).format(candidate.n_groups, candidate.examples)
        )
        intro.setWordWrap(True)
        self.channels_layout.addWidget(intro)
        evidence = QLabel(candidate.evidence)
        evidence.setWordWrap(True)
        self.channels_layout.addWidget(evidence)

        self.channels_check = QCheckBox(
            self.tr("Each set is one recording, with a channel per file")
        )
        self.channels_check.toggled.connect(self.view_model.set_channels_enabled)
        self.channels_layout.addWidget(self.channels_check)

        self.channels_table = QTableWidget(len(state.channels), 3)
        self.channels_table.setHorizontalHeaderLabels(
            [self.tr("Channel"), self.tr("File name ends with"), self.tr("Talker")]
        )
        self.channels_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        for row, channel in enumerate(state.channels):
            self.channels_table.setItem(row, 0, QTableWidgetItem(channel.label))
            self.channels_table.setItem(
                row,
                1,
                QTableWidgetItem(
                    channel.suffix or self.tr("(nothing: the plain name)")
                ),
            )

            combo = QComboBox()
            combo.setEditable(True)
            line_edit = combo.lineEdit()
            if line_edit is not None:
                line_edit.setPlaceholderText(self.tr("describe this channel"))
                line_edit.editingFinished.connect(
                    lambda index=row, combo=combo: self.view_model.set_channel_talker(
                        index, combo.currentText()
                    )
                )
            combo.activated.connect(
                lambda _, index=row, combo=combo: self.view_model.set_channel_talker(
                    index, combo.currentText()
                )
            )
            self.channels_table.setCellWidget(row, 2, combo)
            self.talker_combos.append(combo)
        header = self.channels_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.channels_table.setFixedHeight(40 + 32 * len(state.channels))
        self.channels_layout.addWidget(self.channels_table)

    def _show_channels(self, state: ProjectLayoutState):
        if state.channel_candidate is None:
            return
        self.channels_check.blockSignals(True)
        self.channels_check.setChecked(state.channels_enabled)
        self.channels_check.blockSignals(False)
        self.channels_table.setEnabled(state.channels_enabled)

        for combo, channel in zip(self.talker_combos, state.channels):
            combo.blockSignals(True)
            if not combo.hasFocus():
                combo.clear()
                combo.addItems(["", *state.talker_names])
                combo.setCurrentText(channel.talker)
            combo.blockSignals(False)

    def _build_levels(self, state: ProjectLayoutState):
        if not state.levels:
            self.levels_group.hide()
            return
        intro = QLabel(
            self.tr(
                "What do the folders at each level stand for? Name a variable "
                "(talker, dialect, condition…) or leave it empty to ignore the level."
            )
        )
        intro.setWordWrap(True)
        self.levels_layout.addWidget(intro)

        table = QTableWidget(len(state.levels), 4)
        table.setHorizontalHeaderLabels(
            [
                self.tr("Level"),
                self.tr("Folders"),
                self.tr("Examples"),
                self.tr("Meaning"),
            ]
        )
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        for row, level in enumerate(state.levels):
            table.setItem(row, 0, QTableWidgetItem(str(level.depth)))
            table.setItem(row, 1, QTableWidgetItem(str(level.n_values)))
            example = QTableWidgetItem(level.examples)
            if level.note:
                example.setToolTip(level.note)
                example.setText(f"{level.examples}   ({level.note})")
            table.setItem(row, 2, example)

            edit = QLineEdit(level.field)
            edit.setPlaceholderText(self.tr("not a variable"))
            edit.editingFinished.connect(
                lambda depth=level.depth, edit=edit: self.view_model.set_level_field(
                    depth, edit.text()
                )
            )
            table.setCellWidget(row, 3, edit)
        header = table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        table.setFixedHeight(40 + 32 * len(state.levels))
        self.levels_layout.addWidget(table)

    def _build_roles(self, state: ProjectLayoutState):
        if not state.roles:
            self.roles_group.hide()
            return
        intro = QLabel(
            self.tr(
                "Files that share a recording's name, such as time series data that "
                "belongs to the audio. Choose to keep with each recording, "
                "and say what they are: a file that holds a tier of the annotation "
                "is an annotation, and the tier needs a name."
            )
        )
        intro.setWordWrap(True)
        self.roles_layout.addWidget(intro)

        table = QTableWidget(len(state.roles), 7)
        table.setHorizontalHeaderLabels(
            [
                self.tr("Keep"),
                self.tr("Name"),
                self.tr("Kind"),
                self.tr("Tier name"),
                self.tr("Files like"),
                self.tr("Files"),
                self.tr("Of recordings"),
            ]
        )
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        for row, role in enumerate(state.roles):
            check = QCheckBox()
            check.setChecked(role.selected)
            check.toggled.connect(
                lambda checked, index=row: self.view_model.set_role_selected(
                    index, checked
                )
            )
            table.setCellWidget(row, 0, check)

            edit = QLineEdit(role.name)
            edit.editingFinished.connect(
                lambda index=row, edit=edit: self.view_model.set_role_name(
                    index, edit.text()
                )
            )
            table.setCellWidget(row, 1, edit)

            tier_edit = QLineEdit(role.tier)
            tier_edit.setPlaceholderText(role.name)
            tier_edit.setEnabled(role.kind == ANNOTATION_KIND)
            tier_edit.editingFinished.connect(
                lambda index=row, edit=tier_edit: self.view_model.set_role_tier(
                    index, edit.text()
                )
            )
            format_button = QPushButton(self.tr("Columns…"))
            format_button.setEnabled(role.kind == ANNOTATION_KIND)
            format_button.clicked.connect(
                lambda _=False, index=row: self.edit_annotation_table(index)
            )
            tier_cell = QWidget()
            tier_layout = QHBoxLayout(tier_cell)
            tier_layout.setContentsMargins(0, 0, 0, 0)
            tier_layout.addWidget(tier_edit, 1)
            tier_layout.addWidget(format_button)

            kind_combo = QComboBox()
            kind_combo.addItem(self.tr("Annotation"), ANNOTATION_KIND)
            kind_combo.addItem(self.tr("Time series data"), "time_series")
            kind_combo.addItem(self.tr("Other"), "other")
            kind_combo.setCurrentIndex(max(kind_combo.findData(role.kind), 0))
            kind_combo.currentIndexChanged.connect(
                lambda _, index=row, combo=kind_combo, tier=tier_edit, button=format_button: (
                    self.on_kind_chosen(index, combo.currentData(), tier, button)
                )
            )
            table.setCellWidget(row, 2, kind_combo)
            table.setCellWidget(row, 3, tier_cell)
            self.role_widgets.append((kind_combo, tier_edit, format_button))
            table.setItem(row, 4, QTableWidgetItem(role.pattern))
            table.setItem(row, 5, QTableWidgetItem(str(role.n_files)))
            table.setItem(row, 6, QTableWidgetItem(f"{role.coverage_percent}%"))
        header = table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        table.setFixedHeight(40 + 32 * min(len(state.roles), 8))
        self.roles_layout.addWidget(table)

    # ------------------------------ state ------------------------------

    @pyqtSlot(object)
    def on_state(self, state: object):
        if not isinstance(state, ProjectLayoutState):
            return
        self.state = state

        if not self._built:
            self._built = True
            self._build_channels(state)
            self._build_levels(state)
            self._build_roles(state)
            self.template_edit.setText(state.filename_template)

        self.summary_label.setText(
            self.tr(
                "Found {} audio files ({} recordings). {} will be imported, {} of "
                "them with an annotation."
            ).format(
                state.n_audio_files,
                state.n_audio,
                state.n_recordings,
                state.n_annotated,
            )
        )

        self._show_annotation_choice(state)
        self._show_annotation_folders(state)
        self._show_unpaired(state)
        self._show_duplicate_audio(state)
        self._show_channels(state)
        self._show_template_status(state)
        self._show_preview(state)

        if self.import_button is not None:
            self.import_button.setEnabled(state.can_import)

    def _show_annotation_choice(self, state: ProjectLayoutState):
        self.annotation_combo.blockSignals(True)
        self.annotation_combo.clear()
        self.annotation_combo.addItem(self.tr("none"), "")
        for ext in state.annotation_exts:
            self.annotation_combo.addItem(f"{ext} ({ANNOTATION_FORMATS[ext]})", ext)
        self.annotation_combo.setCurrentIndex(
            max(self.annotation_combo.findData(state.annotation_ext), 0)
        )
        self.annotation_combo.blockSignals(False)
        self.annotation_note.setText(
            self.tr("{} of {} audio files have one").format(
                state.n_audio - state.n_unpaired_audio,
                state.n_audio,
            )
            if state.annotation_ext
            else self.tr("Recordings will be imported without annotations")
        )

    def _fill_folder_choice(
        self, combo: QComboBox, folders: list[FolderChoiceState], current: str
    ):
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(self.tr("any folder"), "")
        for folder in folders:
            combo.addItem(
                self.tr("{} ({} files)").format(
                    folder.folder or self.tr("the project folder itself"),
                    folder.n_files,
                ),
                folder.folder,
            )
        combo.setCurrentIndex(max(combo.findData(current), 0))
        combo.blockSignals(False)

    def _show_annotation_folders(self, state: ProjectLayoutState):
        """Annotations kept in several folders: the user says which folder to read"""
        self.folder_widget.setVisible(len(state.annotation_folders) > 1)
        self._fill_folder_choice(
            self.folder_combo, state.annotation_folders, state.annotation_dir
        )
        self.folder_note.setText(
            self.tr(
                "Several folders hold annotations of the same recordings, so one "
                "has to be chosen."
            )
            if state.annotation_folders_overlap and state.annotation_dir == ""
            else ""
        )

    def _show_unpaired(self, state: ProjectLayoutState):
        if state.n_unpaired_audio == 0:
            self.unpaired_audio_label.setText(
                self.tr("Every audio file has an annotation.")
            )
            self.leave_out_check.setEnabled(False)
        else:
            examples = "\n".join(state.unpaired_audio_examples)
            more = state.n_unpaired_audio - len(state.unpaired_audio_examples)
            self.unpaired_audio_label.setText(
                self.tr("{} audio files have no annotation, for example:\n{}{}").format(
                    state.n_unpaired_audio,
                    examples,
                    self.tr("\n… and {} more").format(more) if more > 0 else "",
                )
            )
            self.leave_out_check.setEnabled(True)
        self.leave_out_check.blockSignals(True)
        self.leave_out_check.setChecked(not state.include_unpaired_audio)
        self.leave_out_check.blockSignals(False)

        if state.n_unpaired_annotations == 0:
            self.unpaired_annotation_label.hide()
        else:
            self.unpaired_annotation_label.show()
            self.unpaired_annotation_label.setText(
                self.tr(
                    "{} annotation files have no audio file, for example:\n{}"
                ).format(
                    state.n_unpaired_annotations,
                    "\n".join(state.unpaired_annotation_examples),
                )
            )

    def _show_duplicate_audio(self, state: ProjectLayoutState):
        self.duplicate_audio_label.setVisible(state.n_duplicate_audio > 0)
        if state.n_duplicate_audio == 0:
            return
        more = state.n_duplicate_audio - len(state.duplicate_audio_examples)
        self.duplicate_audio_label.setText(
            self.tr(
                "Warning: {} audio files look like copies of others (same name and "
                "size in another folder). Each is imported as a unique recording; "
                "delete the copies, or move them out of the project, if that "
                "is not what you want. For example:\n{}{}"
            ).format(
                state.n_duplicate_audio,
                "\n".join(state.duplicate_audio_examples),
                self.tr("\n… and {} more").format(more) if more > 0 else "",
            )
        )

    def _show_template_status(self, state: ProjectLayoutState):
        if state.template_error:
            self.template_status.setStyleSheet("color: #b00020;")
            self.template_status.setText(state.template_error)
        elif state.n_template_mismatches > 0:
            self.template_status.setStyleSheet("color: #b36b00;")
            self.template_status.setText(
                self.tr(
                    "{} file names do not fit the template, for example: {}"
                ).format(
                    state.n_template_mismatches,
                    ", ".join(state.template_mismatch_examples),
                )
            )
        else:
            self.template_status.setStyleSheet("")
            self.template_status.setText("")

    def _show_preview(self, state: ProjectLayoutState):
        table = self.preview_table
        table.clear()
        table.setColumnCount(len(state.preview_headers))
        table.setRowCount(len(state.preview_rows))
        table.setHorizontalHeaderLabels(state.preview_headers)
        for row, values in enumerate(state.preview_rows):
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(value))
        table.resizeColumnsToContents()

    # ------------------------------ actions ------------------------------

    @pyqtSlot(int)
    def on_annotation_changed(self, index: int):
        self.view_model.set_annotation_ext(self.annotation_combo.itemData(index) or "")

    def on_kind_chosen(
        self, index: int, kind: str, tier: QLineEdit, button: QPushButton
    ):
        """What a kind of extra file is. For an annotation, the user is asked how its
        files are read as a table, as soon as it is chosen."""
        annotation = kind == ANNOTATION_KIND
        tier.setEnabled(annotation)
        button.setEnabled(annotation)
        self.view_model.set_role_kind(index, kind)
        if annotation:
            self.edit_annotation_table(index)

    def edit_annotation_table(self, index: int):
        """Asks how the files are read; the tier box then shows the name of the tier,
        which the user may have changed (it is the heading of the label column)"""
        if AnnotationTableDialog.edit(self.view_model, index, self):
            tier = self.view_model.candidates[index].role.tier
            self.role_widgets[index][1].setText(tier)

    @pyqtSlot(int)
    def on_annotation_folder_changed(self, index: int):
        self.view_model.set_annotation_dir(self.folder_combo.itemData(index) or "")

    @pyqtSlot(bool)
    def on_leave_out_toggled(self, checked: bool):
        self.view_model.set_include_unpaired_audio(not checked)

    def accept_layout(self):
        try:
            self.view_model.save_project_layout()
        except Exception as err:  # noqa: BLE001
            QMessageBox.critical(self, self.tr("Project Layout"), str(err))
            return
        self.accept()
