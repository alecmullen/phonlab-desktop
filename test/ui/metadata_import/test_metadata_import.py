from pathlib import Path

import pytest
from PyQt6.QtWidgets import QDialog, QMessageBox
from pytestqt.qtbot import QtBot
from support.view_models import make_metadata_import_view_model

from core.annotation.entity.metadata import MetadataTarget
from core.annotation.entity.recording import Recording
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from core.import_metadata.entity.information_source import InformationSource
from core.import_metadata.information_sources_file import LoadInformationSources
from ui.metadata_import.metadata_import_dialog import MetadataImportDialog
from ui.metadata_import.metadata_import_view_model import MetadataImportViewModel
from ui.metadata_import.state.metadata_import_state import MetadataImportState


def project() -> InMemAnnotationRepository:
    repository = InMemAnnotationRepository()
    repository.upsert_recordings(
        [
            Recording("t1/a", audio_file="t1/a.wav", talkers=["Ann"]),
            Recording("t1/b", audio_file="t1/b.wav", talkers=["Ann"]),
            Recording("t2/a", audio_file="t2/a.wav", talkers=["Bob"]),
        ]
    )
    return repository


def csv(tmp_path: Path, text: str) -> str:
    path = tmp_path / "info.csv"
    path.write_text(text)
    return str(path)


def prepared(
    tmp_path: Path, text: str, repository: InMemAnnotationRepository | None = None
) -> tuple[
    MetadataImportViewModel, list[MetadataImportState], InMemAnnotationRepository
]:
    repository = repository or project()
    view_model = make_metadata_import_view_model(
        str(tmp_path), csv(tmp_path, text), repository
    )
    states: list[MetadataImportState] = []
    view_model.subscribe(states.append)
    view_model.prepare()
    return view_model, states, repository


TALKER_CSV = "age,talker,sex\n31,Ann,F\n45,Bob,M\n"
RECORDING_CSV = "rate,file\n4.5,t1/a\n5.0,t1/b\n"


# --------------------------- view model ---------------------------


def test_a_file_of_talkers_is_recognized_and_its_key_column_found(tmp_path: Path):
    _, states, _ = prepared(tmp_path, TALKER_CSV)

    state = states[-1]
    assert state.target == "talker"
    assert state.key_column == "talker"
    assert (state.n_rows, state.n_matched) == (2, 2)
    assert [c.source for c in state.columns] == ["age", "sex"]
    assert [c.sql_type for c in state.columns] == ["INTEGER", "TEXT"]
    assert state.can_import is True


def test_a_file_of_recordings_is_recognized(tmp_path: Path):
    _, states, _ = prepared(tmp_path, RECORDING_CSV)

    state = states[-1]
    assert (state.target, state.key_column) == ("recording", "file")
    assert state.n_unmatched_targets == 1
    assert state.unmatched_target_examples == ["t2/a"]


def test_a_file_that_names_nothing_in_the_project_cannot_be_imported(tmp_path: Path):
    _, states, _ = prepared(tmp_path, "talker,age\nNobody,3\n")

    assert states[-1].n_matched == 0
    assert states[-1].can_import is False
    assert states[-1].unmatched_examples == ["Nobody"]


def test_unlinked_rows_are_reported(tmp_path: Path):
    _, states, _ = prepared(tmp_path, "talker,age\nAnn,3\nZed,4\n")

    assert (states[-1].n_rows, states[-1].n_matched) == (2, 1)
    assert states[-1].unmatched_examples == ["Zed"]
    assert states[-1].unmatched_target_examples == ["Bob"]


def test_the_user_can_switch_what_the_rows_are_about(tmp_path: Path):
    view_model, states, _ = prepared(tmp_path, TALKER_CSV)

    view_model.set_target("recording")

    assert states[-1].target == "recording"
    assert states[-1].n_matched == 0
    assert states[-1].can_import is False


def test_the_user_can_choose_the_key_column(tmp_path: Path):
    view_model, states, _ = prepared(tmp_path, "who,alias,age\nx,Ann,3\ny,Bob,4\n")

    assert states[-1].key_column == "alias"  # found by trying each column
    view_model.set_key_column("who")

    assert states[-1].n_matched == 0


def test_columns_can_be_left_out_and_renamed(tmp_path: Path):
    view_model, states, repository = prepared(tmp_path, TALKER_CSV)

    view_model.set_column_selected("sex", False)
    view_model.set_column_name("age", "Age (years)")

    assert [(c.name, c.selected) for c in states[-1].columns] == [
        ("Age_years", True),
        ("sex", False),
    ]
    view_model.import_information()
    assert repository.read_metadata(MetadataTarget.TALKER) == {
        "Ann": {"Age_years": 31},
        "Bob": {"Age_years": 45},
    }


def test_importing_stores_values_on_the_matching_recordings(tmp_path: Path):
    view_model, _, repository = prepared(tmp_path, RECORDING_CSV)

    result = view_model.import_information()

    assert result.n_rows == 2
    assert repository.read_metadata(MetadataTarget.RECORDING) == {
        "t1/a": {"rate": 4.5},
        "t1/b": {"rate": 5.0},
    }


def test_a_file_with_no_rows_is_rejected(tmp_path: Path):
    view_model = make_metadata_import_view_model(
        str(tmp_path), csv(tmp_path, "talker,age\n"), project()
    )

    with pytest.raises(ValueError):
        view_model.prepare()


# --------------------------- dialog ---------------------------


def make_dialog(qtbot: QtBot, tmp_path: Path, text: str) -> MetadataImportDialog:
    view_model, _, _ = prepared(tmp_path, text)
    dialog = MetadataImportDialog(view_model)
    qtbot.addWidget(dialog)
    return dialog


def test_dialog_offers_talkers_or_recordings(qtbot: QtBot, tmp_path: Path):
    dialog = make_dialog(qtbot, tmp_path, TALKER_CSV)

    assert dialog.talkers_radio.text() == "Information about talkers"
    assert dialog.recordings_radio.text() == "Information about recordings"
    assert dialog.talkers_radio.isChecked() is True
    assert dialog.key_combo.currentText() == "talker"
    assert dialog.table.rowCount() == 2
    assert "2 of 2 rows match talkers" in dialog.match_label.text()


def test_choosing_recordings_changes_the_match(qtbot: QtBot, tmp_path: Path):
    dialog = make_dialog(qtbot, tmp_path, TALKER_CSV)

    dialog.recordings_radio.setChecked(True)

    assert dialog.state.target == "recording"
    assert dialog.add_button is not None and dialog.add_button.isEnabled() is False


def test_info_button_opens_the_explanation(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    dialog = make_dialog(qtbot, tmp_path, TALKER_CSV)
    shown: list[str] = []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: shown.append(self.text()))

    dialog.info_button.click()

    assert dialog.info_button.text() == "i"
    [text] = [" ".join(t.split()) for t in shown]
    assert "one row per talker" in text
    assert "one row per recording" in text
    assert "'age', 'race', 'gender'" in text


def test_adding_asks_first_when_some_rows_link_to_nothing(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    dialog = make_dialog(qtbot, tmp_path, "talker,age\nAnn,3\nZed,4\n")
    questions: list[str] = []

    def decline(*args: object, **kwargs: object) -> QMessageBox.StandardButton:
        questions.append(str(args[2]))
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", staticmethod(decline))

    dialog.accept_import()

    assert dialog.result() != QDialog.DialogCode.Accepted
    assert "1 of the 2 rows" in questions[0]
    assert (
        dialog.view_model.match_metadata.annotation_repository.read_metadata(
            MetadataTarget.TALKER
        )
        == {}
    )


def test_adding_when_every_row_links_goes_ahead_and_reports(
    qtbot: QtBot, tmp_path: Path
):
    dialog = make_dialog(qtbot, tmp_path, TALKER_CSV)

    dialog.accept_import()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert "Added 2 columns (age, sex) to 2 talkers" in dialog.result_text


# --------------------------- remembering the file for a rebuilt database ---------------------------


def test_adding_information_remembers_the_file_and_what_was_chosen(tmp_path: Path):
    view_model, _, _ = prepared(tmp_path, TALKER_CSV)
    view_model.set_column_selected("sex", False)
    view_model.set_column_name("age", "Age in years")

    view_model.import_information()

    [source] = LoadInformationSources()(str(tmp_path))
    assert source == InformationSource(
        "info.csv", MetadataTarget.TALKER, "talker", {"age": "Age in years"}
    )


def test_nothing_is_remembered_when_the_information_could_not_be_added(
    tmp_path: Path,
):
    view_model, _, _ = prepared(tmp_path, "talker,age\nNobody,3\n")

    with pytest.raises(ValueError):
        view_model.import_information()

    assert LoadInformationSources()(str(tmp_path)) == []


# --------------------------- when the rows are known to be about talkers ---------------------------


def test_a_fixed_target_is_not_asked_about(tmp_path: Path):
    csv = tmp_path / "info.csv"
    csv.write_text("talker,age\nt1,31\n")
    repository = InMemAnnotationRepository()
    repository.upsert_recordings([Recording("a", talkers=["t1"])])
    view_model = make_metadata_import_view_model(
        str(tmp_path), str(csv), repository, MetadataTarget.TALKER
    )
    states: list = []
    view_model.subscribe(states.append)

    view_model.prepare()

    assert states[-1].target == "talker" and states[-1].target_locked is True
    assert states[-1].key_column == "talker"


def test_the_dialog_does_not_offer_the_choice_when_the_target_is_fixed(
    qtbot: QtBot, tmp_path: Path
):
    csv = tmp_path / "info.csv"
    csv.write_text("talker,age\nt1,31\n")
    repository = InMemAnnotationRepository()
    repository.upsert_recordings([Recording("a", talkers=["t1"])])
    view_model = make_metadata_import_view_model(
        str(tmp_path), str(csv), repository, MetadataTarget.TALKER
    )
    view_model.prepare()

    dialog = MetadataImportDialog(view_model)
    qtbot.addWidget(dialog)

    assert dialog.about_group.isHidden()
    assert dialog.windowTitle() == "Add Talkers"
