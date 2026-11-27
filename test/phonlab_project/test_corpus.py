from pathlib import Path

from support.audio_files import write_wavs

from phonlab_project import import_project, open_project
from phonlab_project.corpus import (
    adopt_corpus_description,
    load_corpus,
    read_corpus_description,
    save_corpus,
)

CDC = (
    "Title:\tCABank CORAAL Corpus\nCreator:\tKendall, Tyler\n"
    "Creator:\tFarrington, Charlie\nLanguage:\teng\n"
    "Description:\t Corpus of Regional African American Language\n\n"
    "Date:\t\t2022\nDOI:\t10.21415/V68B-VW06\nNo value\n"
)


def test_a_description_file_gives_one_value_a_name_or_a_list_for_a_repeated_name(
    tmp_path: Path,
):
    (tmp_path / "0metadata.cdc").write_text(CDC, encoding="utf-8")

    info = read_corpus_description(tmp_path / "0metadata.cdc")

    assert info == {
        "title": "CABank CORAAL Corpus",
        "creator": ["Kendall, Tyler", "Farrington, Charlie"],
        "language": "eng",
        "description": "Corpus of Regional African American Language",
        "date": "2022",
        "doi": "10.21415/V68B-VW06",
    }


def test_the_corpus_is_saved_in_its_own_section_and_the_rest_of_the_file_is_kept(
    tmp_path: Path,
):
    (tmp_path / "phonlab.toml").write_text("[import]\nversion = 1\n", encoding="utf-8")

    save_corpus(tmp_path, {"title": "T", "creator": ["A", "B"]})

    assert load_corpus(tmp_path) == {"title": "T", "creator": ["A", "B"]}
    assert "[import]" in (tmp_path / "phonlab.toml").read_text(encoding="utf-8")


def test_a_project_with_no_corpus_section_has_an_empty_corpus(tmp_path: Path):
    assert load_corpus(tmp_path) == {}


def test_the_description_file_in_a_folder_of_the_project_is_adopted_once(
    tmp_path: Path,
):
    (tmp_path / "Annotation").mkdir()
    (tmp_path / "Annotation" / "0metadata.cdc").write_text(CDC, encoding="utf-8")

    assert adopt_corpus_description(tmp_path) is True
    assert load_corpus(tmp_path)["title"] == "CABank CORAAL Corpus"

    save_corpus(tmp_path, {"title": "Edited by hand"})
    assert adopt_corpus_description(tmp_path) is False
    assert load_corpus(tmp_path) == {"title": "Edited by hand"}


def test_importing_a_project_keeps_the_corpus_description_with_it(tmp_path: Path):
    write_wavs(tmp_path, ["a.wav"])
    (tmp_path / "0metadata.cdc").write_text(CDC, encoding="utf-8")

    import_project(tmp_path)

    with open_project(tmp_path) as project:
        assert project.corpus()["doi"] == "10.21415/V68B-VW06"
