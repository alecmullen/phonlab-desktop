from pathlib import Path

from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from core.import_metadata.apply_information_sources import ApplyInformationSources
from core.import_metadata.entity.information_source import InformationSource
from core.import_metadata.import_metadata import ImportMetadata
from core.import_metadata.information_sources_file import (
    LoadInformationSources,
    SaveInformationSource,
    resolved_file_name,
    stored_file_name,
)
from core.import_metadata.match_metadata import MatchMetadata
from core.import_words.entity.word_table import WordSource
from core.import_words.import_words import ImportWords
from core.import_words.word_source_file import LoadWordSource, SaveWordSource
from core.project_layout.project_layout_file import (
    LoadProjectLayout,
    SaveProjectLayout,
)
from phonlab_project.layout.project_layout import FolderLevel, ProjectLayout
from phonlab_project.metadata import MetadataTarget
from phonlab_project.readers.read_metadata_csv import ReadMetadataCsv
from phonlab_project.recording import Recording

TALKERS = InformationSource(
    "talkers.csv", MetadataTarget.TALKER, "talker", {"age": "age", "sex": "Sex"}
)
ITEMS = InformationSource(
    "info/items.csv", MetadataTarget.RECORDING, "file", {"speech rate": "rate"}
)


# --------------------------- the project file ---------------------------


def test_nothing_is_remembered_without_a_project_file(tmp_path: Path):
    assert LoadInformationSources()(str(tmp_path)) == []


def test_sources_are_remembered_in_the_order_they_were_added(tmp_path: Path):
    SaveInformationSource()(str(tmp_path), TALKERS)
    SaveInformationSource()(str(tmp_path), ITEMS)

    assert LoadInformationSources()(str(tmp_path)) == [TALKERS, ITEMS]


def test_adding_a_file_again_replaces_what_was_remembered_about_it(tmp_path: Path):
    SaveInformationSource()(str(tmp_path), TALKERS)
    changed = InformationSource(
        "talkers.csv", MetadataTarget.TALKER, "name", {"age": "years"}
    )

    SaveInformationSource()(str(tmp_path), changed)

    assert LoadInformationSources()(str(tmp_path)) == [changed]


def test_one_file_can_be_remembered_for_talkers_and_for_recordings(tmp_path: Path):
    both = InformationSource("all.csv", MetadataTarget.RECORDING, "file", {})
    SaveInformationSource()(str(tmp_path), TALKERS)
    SaveInformationSource()(str(tmp_path), both)
    SaveInformationSource()(
        str(tmp_path), InformationSource("all.csv", MetadataTarget.TALKER, "t", {})
    )

    assert len(LoadInformationSources()(str(tmp_path))) == 3


def test_remembering_sources_keeps_the_layout_and_the_layout_keeps_the_sources(
    tmp_path: Path,
):
    layout = ProjectLayout(levels=(FolderLevel(1, "talker"),))
    SaveProjectLayout()(str(tmp_path), layout)
    SaveInformationSource()(str(tmp_path), TALKERS)

    SaveProjectLayout()(str(tmp_path), layout)

    assert LoadProjectLayout()(str(tmp_path)) == layout
    assert LoadInformationSources()(str(tmp_path)) == [TALKERS]


def test_entries_that_cannot_be_understood_are_left_out(tmp_path: Path):
    (tmp_path / "phonlab.toml").write_text(
        '[[information]]\nfile = "a.csv"\n\n'
        '[[information]]\nfile = "b.csv"\nabout = "nonsense"\nkey = "k"\n\n'
        '[[information]]\nfile = "c.csv"\nabout = "talker"\nkey = "talker"\n'
    )

    [source] = LoadInformationSources()(str(tmp_path))

    assert source.file == "c.csv"


def test_a_broken_project_file_remembers_nothing(tmp_path: Path):
    (tmp_path / "phonlab.toml").write_text("not [valid")

    assert LoadInformationSources()(str(tmp_path)) == []


def test_files_inside_the_project_are_stored_relative_to_it(tmp_path: Path):
    assert stored_file_name(str(tmp_path), str(tmp_path / "info" / "a.csv")) == (
        "info/a.csv"
    )
    assert resolved_file_name(str(tmp_path), "info/a.csv") == str(
        tmp_path / "info" / "a.csv"
    )


def test_files_outside_the_project_are_stored_in_full(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    outside = str(tmp_path / "elsewhere.csv")

    assert stored_file_name(str(project), outside) == outside
    assert resolved_file_name(str(project), outside) == outside


# --------------------------- adding them again ---------------------------


def make_use_case() -> tuple[ApplyInformationSources, InMemAnnotationRepository]:
    repository = InMemAnnotationRepository()
    repository.upsert_recordings(
        [
            Recording("t1/a", audio_file="t1/a.wav", talkers=["Ann"]),
            Recording("t2/b", audio_file="t2/b.wav", talkers=["Bob"]),
        ]
    )
    return (
        ApplyInformationSources(
            LoadInformationSources(),
            ReadMetadataCsv(),
            MatchMetadata(repository),
            ImportMetadata(repository),
        ),
        repository,
    )


def write_project(tmp_path: Path) -> None:
    (tmp_path / "talkers.csv").write_text("talker,age,sex\nAnn,31,F\nBob,45,M\n")
    (tmp_path / "info").mkdir()
    (tmp_path / "info" / "items.csv").write_text("file,speech rate\nt1/a,4.5\nt2/b,5\n")
    SaveInformationSource()(str(tmp_path), TALKERS)
    SaveInformationSource()(str(tmp_path), ITEMS)


def test_every_remembered_file_is_added_again(tmp_path: Path):
    use_case, repository = make_use_case()
    write_project(tmp_path)

    result = use_case(str(tmp_path))

    assert result.applied == ["talkers.csv", "info/items.csv"]
    assert result.failed == []
    assert repository.read_metadata(MetadataTarget.TALKER) == {
        "Ann": {"age": 31, "Sex": "F"},
        "Bob": {"age": 45, "Sex": "M"},
    }
    assert repository.read_metadata(MetadataTarget.RECORDING) == {
        "t1/a": {"rate": 4.5},
        "t2/b": {"rate": 5.0},
    }


def test_a_project_that_remembers_nothing_adds_nothing(tmp_path: Path):
    use_case, _ = make_use_case()

    result = use_case(str(tmp_path))

    assert (result.applied, result.failed) == ([], [])


def test_a_missing_file_is_reported_and_the_others_are_still_added(tmp_path: Path):
    use_case, repository = make_use_case()
    write_project(tmp_path)
    (tmp_path / "talkers.csv").unlink()

    result = use_case(str(tmp_path))

    assert result.failed == ["talkers.csv"]
    assert result.applied == ["info/items.csv"]
    assert repository.read_metadata(MetadataTarget.TALKER) == {}


def test_a_file_that_lost_its_key_column_is_reported(tmp_path: Path):
    use_case, _ = make_use_case()
    write_project(tmp_path)
    (tmp_path / "talkers.csv").write_text("name,age,sex\nAnn,31,F\n")

    assert use_case(str(tmp_path)).failed == ["talkers.csv"]


def test_a_file_whose_rows_no_longer_match_anything_is_reported(tmp_path: Path):
    use_case, _ = make_use_case()
    write_project(tmp_path)
    (tmp_path / "talkers.csv").write_text("talker,age,sex\nNobody,31,F\n")

    assert use_case(str(tmp_path)).failed == ["talkers.csv"]


def test_columns_the_file_no_longer_has_are_skipped(tmp_path: Path):
    use_case, repository = make_use_case()
    write_project(tmp_path)
    (tmp_path / "talkers.csv").write_text("talker,age\nAnn,31\n")

    result = use_case(str(tmp_path))

    assert "talkers.csv" in result.applied
    assert repository.read_metadata(MetadataTarget.TALKER)["Ann"] == {"age": 31}


# --------------------------- the table of words ---------------------------


def make_use_case_with_words() -> tuple[
    ApplyInformationSources, InMemAnnotationRepository
]:
    repository = InMemAnnotationRepository()
    return (
        ApplyInformationSources(
            LoadInformationSources(),
            ReadMetadataCsv(),
            MatchMetadata(repository),
            ImportMetadata(repository),
            LoadWordSource(),
            ImportWords(repository),
        ),
        repository,
    )


def test_the_table_of_words_is_made_again_with_the_columns_chosen_before(
    tmp_path: Path,
):
    use_case, repository = make_use_case_with_words()
    (tmp_path / "words.csv").write_text("word,freq,pos\nthe,5,det\ncat,2,noun\n")
    SaveWordSource()(str(tmp_path), WordSource("words.csv", "word", {"freq": "count"}))

    result = use_case(str(tmp_path))

    assert result.applied == ["words.csv"] and result.failed == []
    assert repository.words == {"the": {"count": 5}, "cat": {"count": 2}}


def test_a_table_of_words_that_is_gone_is_reported_and_the_rest_still_added(
    tmp_path: Path,
):
    use_case, repository = make_use_case_with_words()
    SaveWordSource()(str(tmp_path), WordSource("missing.csv", "word", {}))

    result = use_case(str(tmp_path))

    assert result.failed == ["missing.csv"] and repository.words == {}
