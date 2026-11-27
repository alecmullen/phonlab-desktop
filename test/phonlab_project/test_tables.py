from pathlib import Path

import pandas as pd
import pytest
from support.textgrid import textgrid_project

from core.project_layout.entity.project_layout import FolderLevel, ProjectLayout
from phonlab_project import (
    ProjectError,
    import_project,
    import_talkers,
    import_words,
    open_project,
)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Talkers aa1 and bb2; the word tier has "hi" and "yo" in each of four recordings,
    and the phone tier h, i, y, o"""
    textgrid_project(tmp_path)
    import_project(tmp_path, ProjectLayout(levels=(FolderLevel(1, "talker"),)))
    return tmp_path


# ------------------------------------ talkers ------------------------------------


def test_what_a_table_says_about_talkers_becomes_columns_of_the_talkers(project: Path):
    table = pd.DataFrame(
        {"speaker": ["aa1", "bb2"], "age": [31, 24], "sex": ["f", "m"]}
    )

    result = import_talkers(project, table)

    assert (result.rows, result.columns) == (2, ["age", "sex"])
    with open_project(project) as p:
        talkers = p.talkers()
        assert talkers.age.tolist() == [31, 24]
        assert talkers.sex.tolist() == ["f", "m"]
        assert str(p.columns("talker").set_index("name").type.age) == "INTEGER"


def test_a_csv_file_can_be_the_table(project: Path, tmp_path: Path):
    csv = tmp_path / "talkers.csv"
    csv.write_text("speaker;height\naa1;1.62\nbb2;1.8\n")

    import_talkers(project, csv)

    with open_project(project) as p:
        assert p.talkers().height.tolist() == [1.62, 1.8]


def test_talkers_are_matched_ignoring_case_and_spaces(project: Path):
    table = pd.DataFrame({"speaker": [" AA1", "Bb2 "], "age": [31, 24]})

    assert import_talkers(project, table).rows == 2


def test_rows_naming_nobody_and_talkers_without_a_row_are_reported(project: Path):
    table = pd.DataFrame({"speaker": ["aa1", "cc3", "aa1"], "age": [31, 99, 32]})

    result = import_talkers(project, table)

    assert result.unmatched_rows == ["cc3"] and result.n_unmatched_rows == 1
    assert result.missing == ["bb2"]
    assert result.duplicates == 1
    with open_project(project) as p:  # the last row for a talker is used
        assert p.talkers().age.tolist()[0] == 32


def test_the_key_and_the_columns_can_be_chosen(project: Path):
    table = pd.DataFrame(
        {"id": [7, 8], "who": ["aa1", "bb2"], "age": [31, 24], "note": ["x", "y"]}
    )

    result = import_talkers(project, table, key="who", columns=["age"])

    assert result.columns == ["age"]
    with open_project(project) as p:
        assert not p.has_column("talker", "note")


def test_column_names_are_made_safe_and_clear_of_the_ones_the_table_has(project: Path):
    table = pd.DataFrame({"speaker": ["aa1"], "Age (years)": [31], "name": ["x"]})

    result = import_talkers(project, table)

    assert result.columns == ["Age_years", "name_2"]


def test_a_column_added_before_is_updated(project: Path):
    import_talkers(project, pd.DataFrame({"speaker": ["aa1"], "age": [31]}))

    import_talkers(project, pd.DataFrame({"speaker": ["aa1"], "age": [32]}))

    with open_project(project) as p:
        assert p.talkers().age.iloc[0] == 32
        assert list(p.talkers().columns).count("age") == 1


def test_empty_cells_stay_empty(project: Path):
    table = pd.DataFrame({"speaker": ["aa1", "bb2"], "age": [31, None]})

    import_talkers(project, table)

    with open_project(project) as p:
        assert pd.isna(p.talkers().age.iloc[1])


def test_a_key_the_table_lacks_raises(project: Path):
    with pytest.raises(ProjectError, match="no column 'who'"):
        import_talkers(project, pd.DataFrame({"speaker": ["aa1"]}), key="who")


def test_a_table_file_that_cannot_be_read_raises(project: Path, tmp_path: Path):
    with pytest.raises(ProjectError, match="Cannot read"):
        import_talkers(project, tmp_path / "missing.csv")


# ------------------------------------- words -------------------------------------


def test_what_a_table_says_about_words_makes_the_word_table(project: Path):
    table = pd.DataFrame(
        {"word": ["hi", "yo"], "pos": ["interjection", "pronoun"], "freq": [10, 3]}
    )

    result = import_words(project, table)

    assert (result.rows, result.columns) == (2, ["pos", "freq"])
    with open_project(project) as p:
        words = p.words(count="phone")
        assert words.pos.tolist() == ["interjection", "pronoun"] * 4
        assert words.n_phone.tolist() == [2] * 8
        assert str(p.columns("word").set_index("name").type.freq) == "INTEGER"


def test_a_word_table_is_replaced_by_the_next(project: Path):
    import_words(project, pd.DataFrame({"word": ["hi"], "pos": ["x"]}))

    import_words(project, pd.DataFrame({"word": ["yo"], "freq": [3]}))

    with open_project(project) as p:
        assert p.columns("word").name.tolist() == ["id", "word", "freq"]
        assert p.connection.execute("SELECT word FROM word").fetchall() == [("yo",)]


def test_words_the_tier_lacks_and_the_table_lacks_are_reported(project: Path):
    table = pd.DataFrame({"word": ["hi", "Hi", "zebra", "hi"], "pos": list("abcd")})

    result = import_words(project, table)

    # compared as written: "Hi" and "zebra" are not in the tier, and "yo" is not in
    # the table; the first of a repeated word is used
    assert result.rows == 3 and result.duplicates == 1
    assert result.unmatched_rows == ["Hi", "zebra"] and result.n_unmatched_rows == 2
    assert result.missing == ["yo"]
    with open_project(project) as p:
        assert p.connection.execute(
            "SELECT pos FROM word WHERE word = 'hi'"
        ).fetchone() == ("a",)


def test_a_long_list_of_unmatched_words_is_cut_short_but_counted(project: Path):
    words = ["hi", *(f"w{n}" for n in range(200))]

    result = import_words(project, pd.DataFrame({"word": words, "n": range(201)}))

    assert result.n_unmatched_rows == 200 and len(result.unmatched_rows) == 50


def test_another_tier_can_be_the_words(project: Path):
    result = import_words(
        project, pd.DataFrame({"phone": ["h", "i"], "kind": ["c", "v"]}), tier="phone"
    )

    assert result.rows == 2 and result.missing == ["o", "y"]


def test_a_tier_the_project_lacks_raises_and_changes_nothing(project: Path):
    import_words(project, pd.DataFrame({"word": ["hi"], "pos": ["x"]}))

    with pytest.raises(ProjectError, match="no tier 'syllable'"):
        import_words(
            project, pd.DataFrame({"word": ["yo"], "pos": ["y"]}), tier="syllable"
        )

    with open_project(project) as p:
        assert p.connection.execute("SELECT word FROM word").fetchall() == [("hi",)]
