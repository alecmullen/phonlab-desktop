from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot
from support.audio_files import write_wavs
from support.project_tree import make_tree
from support.view_models import make_project_layout_view_model

from core.read_tiers.entity.table_format import ColumnRole, TimeUnit
from ui.project_layout.component.annotation_table_dialog import AnnotationTableDialog
from ui.project_layout.project_layout_view_model import ProjectLayoutViewModel

HEADER = "MillisecondsPerFrame: 1.0\r\nEND OF HEADER\r\n"


def tier_project(root: Path) -> Path:
    """Recordings 2.5 s long, each with a table of phones with times in milliseconds"""
    write_wavs(root, ["s1.wav", "s2.wav"], frames=20000, fs=8000)
    for stem in ("s1", "s2"):
        (root / f"{stem}_phn.txt").write_bytes(
            (HEADER + "0.0 400.0 h\r\n400.0 2500.0 ay\r\n").encode()
        )
    return root


def annotation_role(root: Path) -> tuple[ProjectLayoutViewModel, int]:
    view_model = make_project_layout_view_model(str(root))
    view_model.prepare()
    index = next(
        i for i, c in enumerate(view_model.candidates) if c.role.name == "phn_txt"
    )
    view_model.set_role_kind(index, "annotation")
    view_model.set_role_tier(index, "Phone")
    return view_model, index


def test_the_table_is_read_and_its_columns_guessed(tmp_path: Path):
    view_model, index = annotation_role(tier_project(tmp_path))

    state = view_model.annotation_table(index)

    assert state.file_name == "s1_phn.txt"
    assert (state.delimiter, state.skip, state.unit_used) == (" ", 2, "milliseconds")
    assert state.columns == ["start", "end", "label"]
    assert state.rows == [["0.0", "400.0", "h"], ["400.0", "2500.0", "ay"]]
    assert state.problem == ""


def test_the_delimiter_and_lines_to_skip_can_be_changed(tmp_path: Path):
    view_model, index = annotation_role(tier_project(tmp_path))

    state = view_model.annotation_table(index, skip=0)

    assert state.skip == 0
    assert state.rows[0][:2] == ["MillisecondsPerFrame:", "1.0"]
    assert state.problem != "" or state.columns[0] != "start"


def test_roles_given_by_the_user_are_checked(tmp_path: Path):
    view_model, index = annotation_role(tier_project(tmp_path))

    ok = view_model.annotation_table(index, " ", 2, "auto", ["start", "end", "label"])
    no_start = view_model.annotation_table(
        index, " ", 2, "auto", ["unknown", "end", "label"]
    )

    assert ok.problem == ""
    assert "start" in no_start.problem


def test_the_format_the_user_chose_is_kept_with_the_kind_of_file(tmp_path: Path):
    view_model, index = annotation_role(tier_project(tmp_path))

    view_model.set_role_table(index, " ", 2, ["start", "end", "label"], "milliseconds")
    view_model.save_project_layout()

    reread = make_project_layout_view_model(str(tmp_path))
    reread.prepare()
    role = next(c.role for c in reread.candidates if c.role.name == "phn_txt")
    assert role.table is not None
    assert (role.table.delimiter, role.table.skip) == (" ", 2)
    assert role.table.columns == (ColumnRole.START, ColumnRole.END, ColumnRole.LABEL)
    assert role.table.unit is TimeUnit.MILLISECONDS


def test_a_kind_with_no_files_to_look_at_says_so(tmp_path: Path):
    make_tree(tmp_path, ["a.wav", "a_phn.txt"])
    view_model = make_project_layout_view_model(str(tmp_path))
    view_model.prepare()  # the kind is not an annotation, so no file is set aside

    state = view_model.annotation_table(0)

    assert state.problem != "" and state.rows == []


# --------------------------- the popup ---------------------------


def test_the_popup_shows_the_table_with_a_role_for_each_column(
    qtbot: QtBot, tmp_path: Path
):
    view_model, index = annotation_role(tier_project(tmp_path))

    dialog = AnnotationTableDialog(view_model, index)
    qtbot.addWidget(dialog)

    assert dialog.columns() == ["start", "end", "label"]
    assert dialog.table.rowCount() == 3  # the roles, then the two rows of data
    assert dialog.table.item(1, 2).text() == "h"  # type: ignore[union-attr]
    assert dialog.skip_box.value() == 2
    assert "milliseconds" in dialog.status_label.text()
    assert dialog.ok_button is not None and dialog.ok_button.isEnabled()


def test_choosing_a_role_that_another_column_has_frees_the_other(
    qtbot: QtBot, tmp_path: Path
):
    view_model, index = annotation_role(tier_project(tmp_path))
    dialog = AnnotationTableDialog(view_model, index)
    qtbot.addWidget(dialog)

    first = dialog.role_combos[0]
    third = dialog.role_combos[2]
    third.setCurrentIndex(third.findData("start"))
    dialog.on_role_chosen(2)

    assert dialog.columns() == ["unknown", "end", "start"]
    assert first.currentData() == "unknown"


def test_a_table_with_no_start_column_cannot_be_accepted(qtbot: QtBot, tmp_path: Path):
    view_model, index = annotation_role(tier_project(tmp_path))
    dialog = AnnotationTableDialog(view_model, index)
    qtbot.addWidget(dialog)

    first = dialog.role_combos[0]
    first.setCurrentIndex(first.findData("unknown"))
    dialog.on_role_chosen(0)

    assert dialog.ok_button is not None and not dialog.ok_button.isEnabled()
    assert dialog.status_label.text() != ""


def test_changing_the_delimiter_reads_the_file_again(qtbot: QtBot, tmp_path: Path):
    view_model, index = annotation_role(tier_project(tmp_path))
    dialog = AnnotationTableDialog(view_model, index)
    qtbot.addWidget(dialog)

    dialog.delimiter_combo.setCurrentIndex(dialog.delimiter_combo.findData(","))
    dialog.reload()

    assert dialog.state.delimiter == ","
    assert dialog.state.problem != ""  # it has no commas, so it is not a table


def test_accepting_tells_the_view_model_how_to_read_the_files(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    view_model, index = annotation_role(tier_project(tmp_path))
    monkeypatch.setattr(AnnotationTableDialog, "exec", lambda self: 1)

    assert AnnotationTableDialog.edit(view_model, index) is True

    role = view_model.candidates[index].role
    assert role.table is not None
    assert role.table.columns == (ColumnRole.START, ColumnRole.END, ColumnRole.LABEL)
    assert role.table.skip == 2


# --------------------------- the heading of the label column is the tier's name ---------------------------


def headings(dialog: AnnotationTableDialog) -> list[str]:
    return [
        dialog.table.horizontalHeaderItem(c).text()  # type: ignore[union-attr]
        for c in range(dialog.table.columnCount())
    ]


def test_the_tier_is_named_by_the_user_else_the_file_else_the_kind_of_file(
    tmp_path: Path,
):
    write_wavs(tmp_path, ["a.wav"], frames=20000, fs=8000)
    (tmp_path / "a_words.csv").write_text("start,end,word\n0,1,hi\n1,2,there\n")
    view_model = make_project_layout_view_model(str(tmp_path))
    view_model.prepare()
    index = 0
    view_model.set_role_kind(index, "annotation")

    assert view_model.annotation_table(index).tier == "word"  # the file's heading

    view_model.set_role_tier(index, "Words")

    assert view_model.annotation_table(index).tier == "Words"  # the user's name


def test_a_file_without_headings_names_the_tier_after_the_kind_of_file(tmp_path: Path):
    view_model, index = annotation_role(tier_project(tmp_path))
    view_model.set_role_tier(index, "")

    assert view_model.annotation_table(index).tier == "phn_txt"


def test_the_popup_shows_the_tier_name_as_the_heading_of_the_label_column(
    qtbot: QtBot, tmp_path: Path
):
    view_model, index = annotation_role(tier_project(tmp_path))

    dialog = AnnotationTableDialog(view_model, index)
    qtbot.addWidget(dialog)

    assert headings(dialog) == ["Column 1", "Column 2", "Phone"]


def test_the_heading_can_be_changed_and_becomes_the_name_of_the_tier(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    view_model, index = annotation_role(tier_project(tmp_path))
    dialog = AnnotationTableDialog(view_model, index)
    qtbot.addWidget(dialog)

    dialog.rename_tier("  Segments ")

    assert headings(dialog)[2] == "Segments"
    monkeypatch.setattr(AnnotationTableDialog, "exec", lambda self: 1)
    # accepting a dialog that was renamed through the same object
    view_model.set_role_table(index, " ", 2, dialog.columns(), "auto", dialog.tier_name)
    assert view_model.candidates[index].role.tier == "Segments"


def test_an_empty_name_is_not_taken(qtbot: QtBot, tmp_path: Path):
    view_model, index = annotation_role(tier_project(tmp_path))
    dialog = AnnotationTableDialog(view_model, index)
    qtbot.addWidget(dialog)

    dialog.rename_tier("   ")

    assert dialog.tier_name == "Phone"


def test_the_name_moves_to_the_column_chosen_as_the_label(qtbot: QtBot, tmp_path: Path):
    view_model, index = annotation_role(tier_project(tmp_path))
    dialog = AnnotationTableDialog(view_model, index)
    qtbot.addWidget(dialog)

    second = dialog.role_combos[1]
    second.setCurrentIndex(second.findData("label"))
    dialog.on_role_chosen(1)

    assert headings(dialog) == ["Column 1", "Phone", "Column 3"]


def test_the_name_chosen_in_the_popup_shows_in_the_wizard_tier_box(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):

    from ui.project_layout.project_layout_dialog import ProjectLayoutDialog

    tier_project(tmp_path)
    view_model = make_project_layout_view_model(str(tmp_path))
    view_model.prepare()
    dialog = ProjectLayoutDialog(view_model)
    qtbot.addWidget(dialog)
    index = next(
        i for i, c in enumerate(view_model.candidates) if c.role.name == "phn_txt"
    )

    def choose(view_model: ProjectLayoutViewModel, index: int, parent=None) -> bool:  # noqa: ANN001
        view_model.set_role_table(
            index, " ", 2, ["start", "end", "label"], "auto", "Seg"
        )
        return True

    monkeypatch.setattr(AnnotationTableDialog, "edit", staticmethod(choose))
    kind, tier, _ = dialog.role_widgets[index]
    kind.setCurrentIndex(kind.findData("annotation"))

    assert tier.text() == "Seg"
