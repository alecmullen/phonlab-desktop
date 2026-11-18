from pathlib import Path

import pytest
from PyQt6.QtWidgets import QFileDialog
from pytestqt.qtbot import QtBot
from support.view_models import make_word_import_view_model

from core.annotation.entity.annotation import AnnotationLabel, AnnotationType
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from core.import_words.word_source_file import LoadWordSource
from ui.word_import.state.word_import_state import WordImportState
from ui.word_import.word_import_dialog import WordImportDialog
from ui.word_import.word_import_view_model import WordImportViewModel


def project(tier: str = "word") -> InMemAnnotationRepository:
    repository = InMemAnnotationRepository()
    id = repository.create_annotation("a")
    repository.create_types(
        id,
        [
            AnnotationType(
                tier,
                [
                    AnnotationLabel(0, 0, word, id=i)
                    for i, word in enumerate(["the", "cat", "the", "sat"])
                ],
            ),
            AnnotationType("phone", [AnnotationLabel(0, 0, "ph", id=9)]),
        ],
    )
    return repository


def words_csv(tmp_path: Path) -> Path:
    path = tmp_path / "words.csv"
    path.write_text("word,freq,pos\nthe,61.3,det\ncat,3,noun\ndog,2,noun\n")
    return path


def prepared(
    tmp_path: Path, repository: InMemAnnotationRepository | None = None
) -> tuple[WordImportViewModel, list[WordImportState], InMemAnnotationRepository]:
    repository = repository or project()
    view_model = make_word_import_view_model(
        str(tmp_path), str(words_csv(tmp_path)), repository
    )
    states: list[WordImportState] = []
    view_model.subscribe(states.append)
    view_model.prepare()
    return view_model, states, repository


def test_the_tier_called_word_is_taken_and_the_match_is_counted(tmp_path: Path):
    _, states, _ = prepared(tmp_path)

    state = states[-1]
    assert (state.tier, state.tiers) == ("word", ["phone", "word"])
    assert (state.n_words, state.n_found, state.n_unmatched) == (3, 2, 1)
    assert (state.n_rows, state.n_extra) == (3, 1)  # dog is not in the project
    assert state.unmatched_examples == ["sat"]
    assert state.key_column == "word"
    assert [(c.name, c.sql_type) for c in state.columns] == [
        ("freq", "REAL"),
        ("pos", "TEXT"),
    ]
    assert state.can_import is True


def test_another_tier_can_be_chosen_as_the_word_tier(tmp_path: Path):
    view_model, states, _ = prepared(tmp_path)

    view_model.set_tier("phone")

    assert states[-1].tier == "phone"
    assert states[-1].n_found == 0 and states[-1].n_unmatched == 1


def test_a_project_without_tiers_cannot_have_words_added(tmp_path: Path):
    view_model = make_word_import_view_model(
        str(tmp_path), str(words_csv(tmp_path)), InMemAnnotationRepository()
    )

    with pytest.raises(ValueError):
        view_model.prepare()


def test_importing_makes_the_word_table_and_remembers_the_file(tmp_path: Path):
    view_model, _, repository = prepared(tmp_path)

    result = view_model.import_words()

    assert result.n_rows == 3
    assert repository.words["the"] == {"freq": 61.3, "pos": "det"}
    source = LoadWordSource()(str(tmp_path))
    assert source is not None
    assert (source.file, source.tier) == ("words.csv", "word")
    assert source.columns == {"freq": "freq", "pos": "pos"}


def test_the_unmatched_words_can_be_saved(tmp_path: Path):
    view_model, _, _ = prepared(tmp_path)
    path = tmp_path / "unmatched.csv"

    n = view_model.save_unmatched(str(path))

    assert n == 1
    assert path.read_text().splitlines() == ["word,count", "sat,1"]


# --------------------------- the dialog ---------------------------


def test_the_dialog_reports_the_match_and_offers_to_save_the_unmatched_words(
    qtbot: QtBot, tmp_path: Path
):
    view_model, _, _ = prepared(tmp_path)

    dialog = WordImportDialog(view_model)
    qtbot.addWidget(dialog)

    text = dialog.match_label.text()
    assert "3 different words; the table has 2 of them" in text
    assert "1 words of the tier are not in the table, for example: sat" in text
    assert "1 words of the table are not in the tier" in text
    assert dialog.save_button.isEnabled()
    assert dialog.table.rowCount() == 2
    assert dialog.tier_combo.currentText() == "word"


def test_choosing_another_tier_updates_the_report(qtbot: QtBot, tmp_path: Path):
    view_model, _, _ = prepared(tmp_path)
    dialog = WordImportDialog(view_model)
    qtbot.addWidget(dialog)

    dialog.tier_combo.setCurrentText("phone")
    dialog.on_tier_chosen(dialog.tier_combo.currentIndex())

    assert "1 different words; the table has 0 of them" in dialog.match_label.text()


def test_saving_the_unmatched_words_asks_for_a_file(
    qtbot: QtBot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    view_model, _, _ = prepared(tmp_path)
    dialog = WordImportDialog(view_model)
    qtbot.addWidget(dialog)
    path = tmp_path / "out.csv"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(path), ""))
    )
    shown: list[str] = []
    monkeypatch.setattr(
        "ui.word_import.word_import_dialog.QMessageBox.information",
        staticmethod(lambda parent, title, text: shown.append(text)),
    )

    dialog.save_unmatched()

    assert path.read_text().splitlines() == ["word,count", "sat,1"]
    assert shown == ["Saved 1 words."]


def test_accepting_adds_the_words_and_says_what_was_made(qtbot: QtBot, tmp_path: Path):
    view_model, _, repository = prepared(tmp_path)
    dialog = WordImportDialog(view_model)
    qtbot.addWidget(dialog)

    dialog.accept_import()

    assert "3 words and 2 columns" in dialog.result_text
    assert "the table has 2 of them" in dialog.result_text
    assert set(repository.words) == {"the", "cat", "dog"}
