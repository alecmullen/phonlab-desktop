from collections.abc import Generator
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot
from support.view_models import make_database_view_model

from core.annotation.entity.metadata import MetadataColumn, MetadataTarget, SqlType
from core.annotation.entity.recording import Recording
from data.annotation.datasource.annotation_datasource import AnnotationDataSource
from data.annotation.repository.annotation_repository import DataAnnotationRepository
from data.base.database import SQLiteDatabase
from ui.database_view.database_dialog import DatabaseDialog
from ui.database_view.database_view_model import DatabaseViewModel
from ui.database_view.state.database_view_state import DatabaseViewState


@pytest.fixture
def repository(tmp_path: Path) -> Generator[DataAnnotationRepository]:
    database = SQLiteDatabase()
    database.connect(str(tmp_path))
    yield DataAnnotationRepository(AnnotationDataSource(database))
    database.engine.dispose()


def project(repository: DataAnnotationRepository) -> DataAnnotationRepository:
    repository.upsert_recordings(
        [
            Recording("t1/a", audio_file="t1/a.wav", talkers=["Ann"]),
            Recording("t2/b", audio_file="t2/b.wav", talkers=["Bob"]),
        ]
    )
    repository.add_metadata(
        MetadataTarget.TALKER,
        [MetadataColumn("age", SqlType.INTEGER)],
        {"Ann": {"age": 31}},
    )
    return repository


def prepared(
    tmp_path: Path, repository: DataAnnotationRepository
) -> tuple[DatabaseViewModel, list[DatabaseViewState]]:
    view_model = make_database_view_model(str(tmp_path), project(repository))
    states: list[DatabaseViewState] = []
    view_model.subscribe(states.append)
    view_model.prepare()
    return view_model, states


def test_the_first_table_is_shown_with_all_its_rows(
    tmp_path: Path, repository: DataAnnotationRepository
):
    _, states = prepared(tmp_path, repository)

    state = states[-1]
    assert state.tables[:3] == ["recording", "talker", "recording_talker"]
    assert "recording_channel" not in state.tables
    assert state.table == "recording"
    assert state.n_rows == state.n_shown == 2
    assert state.columns[:2] == ["id", "file_stem"]
    assert state.rows[0][1] == "t1/a"


def test_added_columns_are_shown_and_empty_values_say_null(
    tmp_path: Path, repository: DataAnnotationRepository
):
    view_model, states = prepared(tmp_path, repository)

    view_model.set_table("talker")

    state = states[-1]
    assert state.columns == ["id", "name", "age"]
    assert state.rows == [["1", "Ann", "31"], ["2", "Bob", "NULL"]]


def test_rows_can_be_filtered(tmp_path: Path, repository: DataAnnotationRepository):
    view_model, states = prepared(tmp_path, repository)

    view_model.set_filter("T2")

    assert states[-1].n_shown == 1
    assert states[-1].rows[0][1] == "t2/b"
    assert states[-1].n_rows == 2


def test_refresh_reads_the_table_again(
    tmp_path: Path, repository: DataAnnotationRepository
):
    view_model, states = prepared(tmp_path, repository)
    view_model.set_table("talker")
    view_model.list_tables.annotation_repository.add_metadata(  # type: ignore[attr-defined]
        MetadataTarget.TALKER,
        [MetadataColumn("sex")],
        {"Ann": {"sex": "F"}},
    )

    view_model.refresh()

    assert states[-1].columns[-1] == "sex"


def test_dialog_shows_the_table_and_a_status(
    qtbot: QtBot, tmp_path: Path, repository: DataAnnotationRepository
):
    view_model, _ = prepared(tmp_path, repository)
    dialog = DatabaseDialog(view_model)
    qtbot.addWidget(dialog)

    assert dialog.table_combo.currentText() == "recording"
    assert dialog.table.rowCount() == 2
    assert dialog.status_label.text() == "2 rows"

    dialog.table_combo.setCurrentIndex(1)
    dialog.on_table_chosen(1)
    qtbot.keyClicks(dialog.filter_edit, "bob")

    assert dialog.table.rowCount() == 1
    assert "1 contain" in dialog.status_label.text()


def test_the_table_linking_recordings_to_talkers_shows_their_names(
    tmp_path: Path, repository: DataAnnotationRepository
):
    view_model, states = prepared(tmp_path, repository)

    view_model.set_table("recording_talker")

    assert states[-1].columns == ["id", "recording", "talker"]
    assert [row[1:] for row in states[-1].rows] == [["t1/a", "Ann"], ["t2/b", "Bob"]]
