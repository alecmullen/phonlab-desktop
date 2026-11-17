from core.annotation.entity.metadata import MetadataTarget, SqlType
from core.annotation.entity.recording import Recording
from core.annotation.repository.in_mem_annotation_repository import (
    InMemAnnotationRepository,
)
from core.import_metadata.entity.metadata_table import MetadataTable
from core.import_metadata.import_metadata import (
    ImportMetadata,
    column_name,
    convert,
    infer_sql_type,
)
from core.import_metadata.match_metadata import MatchMetadata


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


def table(headers: list[str], *rows: list[str]) -> MetadataTable:
    return MetadataTable(headers, list(rows))


# --------------------------- matching ---------------------------


def test_talker_rows_match_talker_names_ignoring_case():
    match = MatchMetadata(project())(
        table(["talker", "age"], ["ann", "31"], [" BOB ", "45"], ["Cy", "9"]),
        MetadataTarget.TALKER,
        "talker",
    )

    assert match.matches == {0: "Ann", 1: "Bob"}
    assert match.unmatched_values == ["Cy"]
    assert (match.n_targets, match.n_unmatched_targets) == (2, 0)


def test_recording_rows_match_file_stems():
    match = MatchMetadata(project())(
        table(["file", "rate"], ["t1/a", "4"], ["t2/a", "5"]),
        MetadataTarget.RECORDING,
        "file",
    )

    assert match.matches == {0: "t1/a", 1: "t2/a"}
    assert match.strategy == "file path"
    assert match.n_unmatched_targets == 1


def test_recording_rows_match_audio_file_names_when_they_are_unique():
    match = MatchMetadata(project())(
        table(["file", "rate"], ["b.wav", "4"]), MetadataTarget.RECORDING, "file"
    )

    assert match.matches == {0: "t1/b"}
    assert match.strategy == "audio file name"


def test_bare_names_shared_by_recordings_are_not_guessed():
    match = MatchMetadata(project())(
        table(["file"], ["a"], ["b"]), MetadataTarget.RECORDING, "file"
    )

    assert match.matches == {1: "t1/b"}
    assert match.unmatched_values == ["a"]


def test_rows_naming_the_same_thing_are_counted():
    match = MatchMetadata(project())(
        table(["talker"], ["Ann"], ["Ann"]), MetadataTarget.TALKER, "talker"
    )

    assert match.n_duplicates == 1


# --------------------------- columns ---------------------------


def test_column_names_are_made_safe_and_distinct():
    taken = {"id", "name"}

    assert column_name("Speech rate (syll/s)", taken) == "Speech_rate_syll_s"
    assert column_name("2nd", taken) == "c_2nd"
    assert column_name("Name", taken) == "Name_2"
    assert column_name("???", taken) == "column"


def test_column_types_follow_the_values():
    assert infer_sql_type(["1", "22", ""]) == SqlType.INTEGER
    assert infer_sql_type(["1.5", "2"]) == SqlType.REAL
    assert infer_sql_type(["1", "x"]) == SqlType.TEXT
    assert infer_sql_type(["", ""]) == SqlType.TEXT


def test_values_are_converted_and_empty_cells_become_none():
    assert convert("12", SqlType.INTEGER) == 12
    assert convert("1.5", SqlType.REAL) == 1.5
    assert convert("", SqlType.REAL) is None
    assert convert("F", SqlType.TEXT) == "F"


# --------------------------- importing ---------------------------


def test_talker_information_is_stored_once_per_talker():
    repository = project()
    metadata = table(["talker", "age", "sex"], ["Ann", "31", "F"], ["Bob", "45", "M"])
    match = MatchMetadata(repository)(metadata, MetadataTarget.TALKER, "talker")
    use_case = ImportMetadata(repository)

    result = use_case(
        metadata,
        match,
        use_case.plan_columns(
            metadata, MetadataTarget.TALKER, {"age": "age", "sex": "sex"}
        ),
    )

    assert result.n_rows == 2
    assert result.columns == ["age", "sex"]
    assert repository.read_metadata(MetadataTarget.TALKER) == {
        "Ann": {"age": 31, "sex": "F"},
        "Bob": {"age": 45, "sex": "M"},
    }


def test_recording_information_goes_with_the_recordings():
    repository = project()
    metadata = table(["file", "rate"], ["t1/a", "4.5"], ["t2/a", ""])
    match = MatchMetadata(repository)(metadata, MetadataTarget.RECORDING, "file")
    use_case = ImportMetadata(repository)

    use_case(
        metadata,
        match,
        use_case.plan_columns(
            metadata, MetadataTarget.RECORDING, {"rate": "speech rate"}
        ),
    )

    assert repository.read_metadata(MetadataTarget.RECORDING) == {
        "t1/a": {"speech_rate": 4.5},
        "t2/a": {"speech_rate": None},
    }


def test_names_that_clash_with_the_columns_phonlab_uses_are_changed():
    repository = project()
    metadata = table(["talker", "name"], ["Ann", "Annabel"])
    use_case = ImportMetadata(repository)

    [plan] = use_case.plan_columns(metadata, MetadataTarget.TALKER, {"name": "name"})

    assert plan.name == "name_2"
