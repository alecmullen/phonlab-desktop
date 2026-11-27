from pathlib import Path

import pytest

from core.annotation.entity.annotation import AnnotationLabel, AnnotationType
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from core.import_words.entity.word_table import WordSource
from core.import_words.import_words import ImportWords
from core.import_words.match_words import MatchWords
from core.import_words.save_unmatched_words import SaveUnmatchedWords
from core.import_words.word_source_file import LoadWordSource, SaveWordSource
from phonlab_project.metadata import SqlType
from phonlab_project.readers.metadata_table import MetadataTable


def project_with_words(words_per_file: list[list[str]]) -> InMemAnnotationRepository:
    repository = InMemAnnotationRepository()
    for number, words in enumerate(words_per_file):
        id = repository.create_annotation(f"f{number}")
        repository.create_types(
            id,
            [
                AnnotationType(
                    "word",
                    [AnnotationLabel(0, 0, word, id=i) for i, word in enumerate(words)],
                ),
                AnnotationType("phone", [AnnotationLabel(0, 0, "ph", id=99)]),
            ],
        )
    return repository


def table(headers: list[str], *rows: list[str]) -> MetadataTable:
    return MetadataTable(headers, [list(row) for row in rows])


# --------------------------- matching ---------------------------


def test_the_words_of_the_tier_the_table_has_and_lacks_are_counted():
    repository = project_with_words([["the", "cat", "the"], ["sat", "the"]])
    words = table(["word", "freq"], ["the", "9"], ["cat", "3"], ["dog", "2"])

    match = MatchWords(repository)(words, "word")

    assert (match.n_words, match.n_found, match.n_rows) == (3, 2, 3)
    assert match.unmatched == {"sat": 1}
    assert (match.n_unmatched, match.n_extra) == (1, 1)  # dog is not in the project


def test_only_the_chosen_tier_counts():
    repository = project_with_words([["the"]])

    match = MatchWords(repository)(table(["w", "x"], ["ph", "1"]), "word")

    assert match.n_found == 0 and match.unmatched == {"the": 1}


def test_the_case_of_a_word_counts_and_repeated_rows_are_noticed():
    repository = project_with_words([["The", "the"]])
    words = table(["word", "x"], ["the", "1"], ["the", "2"], ["", "3"])

    match = MatchWords(repository)(words, "word")

    assert match.n_found == 1 and match.unmatched == {"The": 1}
    assert (match.n_rows, match.n_duplicates) == (2, 1)  # the empty word is not a row


# --------------------------- adding the table ---------------------------


def test_the_columns_after_the_first_become_typed_columns_of_the_word_table():
    repository = InMemAnnotationRepository()
    importer = ImportWords(repository)
    words = table(
        ["Word", "Freq per million", "pos"],
        ["the", "61.3", "det"],
        ["cat", "3", "noun"],
        ["the", "99", "x"],
        ["", "1", "y"],
    )

    plans = importer.plan_columns(words)
    result = importer(words, plans)

    assert [(p.name, p.sql_type) for p in plans] == [
        ("Freq_per_million", SqlType.REAL.value),
        ("pos", SqlType.TEXT.value),
    ]
    assert result.n_rows == 2  # the first "the" is kept, the empty word is not a word
    assert repository.words == {
        "the": {"Freq_per_million": 61.3, "pos": "det"},
        "cat": {"Freq_per_million": 3.0, "pos": "noun"},
    }


def test_column_names_do_not_clash_with_those_the_word_table_has():
    plans = ImportWords(InMemAnnotationRepository()).plan_columns(
        table(["w", "id", "word", "x"], ["a", "1", "b", "2"])
    )

    assert [p.name for p in plans] == ["id_2", "word_2", "x"]


def test_only_the_wanted_columns_are_planned_and_renamed():
    plans = ImportWords(InMemAnnotationRepository()).plan_columns(
        table(["w", "a", "b"], ["x", "1", "2"]), {"b": "bee"}
    )

    assert [(p.source, p.name) for p in plans] == [("b", "bee")]


# --------------------------- saving ---------------------------


def test_unmatched_words_are_saved_most_frequent_first(tmp_path: Path):
    path = tmp_path / "unmatched.csv"

    n = SaveUnmatchedWords()(str(path), {"b": 2, "a": 2, "c": 9})

    assert n == 3
    assert path.read_text().splitlines() == ["word,count", "c,9", "a,2", "b,2"]


def test_the_word_source_is_remembered_in_the_project_file(tmp_path: Path):
    (tmp_path / "phonlab.toml").write_text("[import]\nversion = 1\n")
    source = WordSource("words.csv", "Word", {"freq": "frequency"})

    SaveWordSource()(str(tmp_path), source)

    assert LoadWordSource()(str(tmp_path)) == source
    assert "[import]" in (tmp_path / "phonlab.toml").read_text()


def test_no_word_source_is_found_when_none_was_saved(tmp_path: Path):
    assert LoadWordSource()(str(tmp_path)) is None


@pytest.mark.parametrize("text", ['[words]\nfile = "a"\n', "not toml ["])
def test_a_word_source_that_cannot_be_understood_is_ignored(tmp_path: Path, text: str):
    (tmp_path / "phonlab.toml").write_text(text)

    assert LoadWordSource()(str(tmp_path)) is None
