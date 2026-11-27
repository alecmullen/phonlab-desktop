import ast
import sqlite3
from pathlib import Path

import pytest

from core.annotation.entity.metadata import MetadataColumn, MetadataTarget, SqlType
from core.annotation.entity.recording import Recording
from core.parse_textgrid.parse_textgrid import ParseTextGrid
from data.annotation.datasource.annotation_datasource import AnnotationDataSource
from data.annotation.repository.annotation_repository import DataAnnotationRepository
from data.base.database import SQLiteDatabase
from phonlab_project import Project, ProjectError, open_project
from phonlab_project.schema import SCHEMA_VERSION

WORDS = ["run", "big", "walk", "red", "jump", "tall"]
PHONES = {
    "run": "ran",
    "big": "big",
    "walk": "wok",
    "red": "red",
    "jump": "jump",
    "tall": "tall",
}


def interval_tier(index: int, name: str, items: list[tuple[float, float, str]]) -> str:
    text = (
        f'    item [{index}]:\n        class = "IntervalTier"\n        name = "{name}"\n'
        f"        xmin = 0\n        xmax = 6\n        intervals: size = {len(items)}\n"
    )
    for number, (begin, end, label) in enumerate(items, 1):
        text += (
            f"        intervals [{number}]:\n            xmin = {begin}\n"
            f'            xmax = {end}\n            text = "{label}"\n'
        )
    return text


def textgrid_text() -> str:
    words = [(i, i + 1, word) for i, word in enumerate(WORDS)]
    phones = []
    for i, word in enumerate(WORDS):
        letters = PHONES[word]
        for n, letter in enumerate(letters):
            step = 1 / len(letters)
            phones.append(
                (round(i + n * step, 6), round(i + (n + 1) * step, 6), letter)
            )
    return (
        'File type = "ooTextFile"\nObject class = "TextGrid"\nxmin = 0\nxmax = 6\n'
        "tiers? <exists>\nsize = 2\nitem []:\n"
        + interval_tier(1, "word", words)
        + interval_tier(2, "phone", phones)
    )


def make_project(directory: Path, with_words: bool = True) -> Path:
    (directory / "s1.TextGrid").write_text(textgrid_text())
    database = SQLiteDatabase()
    database.connect(str(directory))
    repository = DataAnnotationRepository(AnnotationDataSource(database))
    repository.upsert_recordings(
        [
            Recording(
                "s1",
                audio_file="s1.wav",
                annotation_file="s1.TextGrid",
                talkers=["Ann"],
                target_talker="aa1",
                fields={"dialect": "north"},
            )
        ]
    )
    next(ParseTextGrid(repository)(str(directory / "s1.TextGrid"), "s1"))
    repository.add_metadata(
        MetadataTarget.TALKER,
        [MetadataColumn("age", SqlType.INTEGER)],
        {"Ann": {"age": 31}},
    )
    if with_words:
        pos = dict(
            zip(WORDS, ["verb", "adjective", "verb", "adjective", "verb", "adjective"])
        )
        repository.replace_words(
            [MetadataColumn("pos")], [(word, {"pos": pos[word]}) for word in WORDS]
        )
    database.engine.dispose()
    return directory


@pytest.fixture
def project(tmp_path: Path):
    with open_project(make_project(tmp_path)) as opened:
        yield opened


def test_a_project_is_opened_from_its_folder_or_its_file(tmp_path: Path):
    make_project(tmp_path)

    with (
        open_project(tmp_path) as by_folder,
        open_project(tmp_path / "phonlab.db") as by_file,
    ):
        assert by_folder.tables() == by_file.tables()


def test_a_folder_with_no_database_is_not_a_project(tmp_path: Path):
    with pytest.raises(ProjectError, match="no project database"):
        open_project(tmp_path)


def test_a_file_that_is_not_a_database_is_not_a_project(tmp_path: Path):
    (tmp_path / "phonlab.db").write_text("not a database at all")

    with pytest.raises(ProjectError, match="not a project database"):
        open_project(tmp_path)


def test_another_database_is_not_a_project(tmp_path: Path):
    sqlite3.connect(tmp_path / "phonlab.db").execute(
        "CREATE TABLE x (a)"
    ).connection.close()

    with pytest.raises(ProjectError, match="no recordings"):
        open_project(tmp_path)


def set_version(directory: Path, version: int) -> None:
    connection = sqlite3.connect(directory / "phonlab.db")
    connection.execute(f"PRAGMA user_version = {version}")
    connection.close()


def test_a_database_the_app_makes_carries_the_schema_version(tmp_path: Path):
    make_project(tmp_path)

    with open_project(tmp_path) as project:
        assert project.schema_version == SCHEMA_VERSION
        stored = project.connection.execute("PRAGMA user_version").fetchone()[0]
        assert stored == SCHEMA_VERSION


def test_a_database_without_a_version_is_read_as_the_first_version(tmp_path: Path):
    make_project(tmp_path)
    set_version(tmp_path, 0)

    with open_project(tmp_path) as project:
        assert project.schema_version == 1


def test_a_database_of_a_newer_schema_is_refused(tmp_path: Path):
    make_project(tmp_path)
    set_version(tmp_path, SCHEMA_VERSION + 1)

    with pytest.raises(ProjectError, match="newer"):
        open_project(tmp_path)


def test_the_database_is_read_only(project: Project):
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        project.connection.execute("DELETE FROM recording")


def test_columns_say_which_are_core_optional_and_added(project: Project):
    kinds = dict(
        zip(project.columns("recording").name, project.columns("recording").kind)
    )

    assert kinds["file_stem"] == "core"
    assert kinds["target_talker"] == "optional"
    assert project.columns("talker").set_index("name").kind["age"] == "added"
    assert project.columns("word").set_index("name").type["pos"] == "TEXT"


def test_a_project_can_be_asked_what_it_has(project: Project):
    assert project.has_column("word", "pos")
    assert not project.has_column("word", "freq")
    assert not project.has_column("nowhere", "pos")
    assert project.has_table("word")
    assert not project.has_table("recording_channel")


def test_columns_of_a_table_the_project_lacks_raise(project: Project):
    with pytest.raises(ProjectError, match="no table called 'recording_channel'"):
        project.columns("recording_channel")


def test_recordings_have_their_added_columns_and_their_fields_expanded(
    project: Project,
):
    [recording] = project.recordings().to_dict("records")

    assert recording["file_stem"] == "s1"
    assert recording["target_talker"] == "aa1"
    assert recording["dialect"] == "north"
    assert "video_file" not in recording  # the project has no video


def test_fields_are_left_alone_when_not_expanded(project: Project):
    recordings = project.recordings(fields=False)

    assert recordings.fields[0] == {"dialect": "north"}
    assert "dialect" not in recordings.columns


def test_talkers_have_their_added_columns(project: Project):
    [talker] = project.talkers().to_dict("records")

    assert (talker["name"], talker["age"]) == ("Ann", 31)
    assert project.recording_talkers().to_dict("records") == [
        {"recording": "s1", "talker": "Ann"}
    ]


def test_tiers_are_listed_with_their_label_counts(project: Project):
    tiers = project.tiers().set_index("tier")

    assert tiers.n_labels["word"] == 6
    assert tiers.n_labels["phone"] == 20
    assert project.tier_names() == ["word", "phone"]


def test_labels_are_one_row_each_with_their_times(project: Project):
    labels = project.labels(tier="word")

    assert list(labels.columns) == ["recording", "tier", "talker", "t1", "t2", "label"]
    assert labels.label.tolist() == WORDS
    assert labels.t1.tolist() == [0, 1, 2, 3, 4, 5]
    assert labels.talker.isna().all()  # no tier says who made it


def test_labels_can_be_limited_to_tiers_and_recordings(project: Project):
    assert len(project.labels()) == 26
    assert len(project.labels(tier=["word", "phone"], recording="s1")) == 26
    assert project.labels(tier="phone").label.tolist()[:3] == ["r", "a", "n"]


def test_a_tier_the_project_lacks_raises_with_the_ones_it_has(project: Project):
    with pytest.raises(
        ProjectError, match=r"no tier \['syllable'\].*\['word', 'phone'\]"
    ):
        project.labels(tier="syllable")


def test_asking_for_a_talker_when_no_tier_has_one_raises(project: Project):
    with pytest.raises(ProjectError, match="cannot be limited to a talker"):
        project.labels(talker="Ann")


def test_labels_name_the_talker_of_a_tier_and_can_be_limited_to_it(tmp_path: Path):
    (tmp_path / "s1.srt").write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nAnn: Hi\n\n"
        "2\n00:00:01,000 --> 00:00:02,000\nBob: Hello\n"
    )
    database = SQLiteDatabase()
    database.connect(str(tmp_path))
    repository = DataAnnotationRepository(AnnotationDataSource(database))
    repository.upsert_recordings([Recording("s1", talkers=["Ann", "Bob"])])
    next(ParseTextGrid(repository)(str(tmp_path / "s1.srt"), "s1"))
    database.engine.dispose()

    with open_project(tmp_path) as srt_project:
        assert srt_project.tiers().talker.tolist() == ["Ann", "Bob"]
        only_bob = srt_project.labels(talker="Bob")
        assert only_bob.label.tolist() == ["Hello"]
        with pytest.raises(ProjectError, match="no talker \\['Cy'\\]"):
            srt_project.labels(talker="Cy")


def test_the_labels_of_a_tier_within_each_label_of_another_are_counted(
    project: Project,
):
    counted = project.count_within("word", "phone")

    assert counted.n_phone.tolist() == [3, 3, 3, 3, 4, 4]
    assert counted.label.tolist() == WORDS


def test_words_have_what_the_word_table_says_and_can_count_their_phones(
    project: Project,
):
    words = project.words(count="phone")

    assert words.pos.tolist() == [
        "verb",
        "adjective",
        "verb",
        "adjective",
        "verb",
        "adjective",
    ]
    assert words.n_phone.tolist() == [3, 3, 3, 3, 4, 4]
    assert (words.t2 - words.t1).tolist() == [1] * 6


def test_the_answer_to_a_question_over_part_of_speech_and_phone_count(project: Project):
    words = project.words(count="phone")
    words["duration"] = words.t2 - words.t1

    by_class = words.groupby(["n_phone", "pos"]).duration.agg(["mean", "count"])

    assert by_class.loc[(3, "verb"), "count"] == 2
    assert by_class.loc[(4, "adjective"), "count"] == 1


def test_words_raise_clearly_when_the_project_has_no_word_table(tmp_path: Path):
    make_project(tmp_path, with_words=False)

    with (
        open_project(tmp_path) as bare,
        pytest.raises(ProjectError, match="no word table"),
    ):
        bare.words()


def test_the_package_does_not_use_the_desktop_app():
    source = Path(__file__).parents[2] / "src" / "phonlab_project"
    imported = set()
    for file in source.glob("*.py"):
        for node in ast.walk(ast.parse(file.read_text())):
            if isinstance(node, ast.Import):
                imported |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                imported.add(node.module.split(".")[0])

    assert not imported & {
        "core",
        "data",
        "ui",
        "res",
        "bootstrap",
        "PyQt6",
        "sqlalchemy",
    }
