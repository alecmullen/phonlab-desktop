import sqlite3
from pathlib import Path

import pytest
from support.audio_files import write_wavs
from support.textgrid import textgrid_project, word_and_phone_textgrid

from core.parse_textgrid.parse_textgrid import ParseTextGrid
from core.project.add_project_files import AddProjectFiles
from core.project.scan_project_files import scan_project_files
from data.annotation.datasource.annotation_datasource import AnnotationDataSource
from data.annotation.repository.annotation_repository import DataAnnotationRepository
from data.base.database import SQLiteDatabase
from phonlab_project import (
    ImportNeedsReview,
    ProjectError,
    add_recordings,
    describe_project,
    import_project,
    open_project,
    schema,
    update_annotations,
)
from phonlab_project.layout.project_layout import FolderLevel, ProjectLayout
from phonlab_project.layout.project_layout_file import load_layout, save_layout

SRT = (
    "1\n00:00:00,000 --> 00:00:01,000\nAnn: Hi there\n\n"
    "2\n00:00:01,000 --> 00:00:02,000\nBob: Hello\n\n"
    "3\n00:00:02,000 --> 00:00:03,000\nAnn: Bye\n"
)


def import_with_the_app(folder: Path) -> None:
    """What the desktop app does to build the database of a project"""
    database = SQLiteDatabase()
    database.connect(str(folder))
    repository = DataAnnotationRepository(AnnotationDataSource(database))
    files = scan_project_files(str(folder))
    list(AddProjectFiles(repository, ParseTextGrid(repository))(files))
    database.close()


def dump(folder: Path) -> dict[str, list[tuple]]:
    """Every row of every table of the database, in order, with its columns"""
    connection = sqlite3.connect(folder / "phonlab.db")
    tables = sorted(
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    )
    result = {
        table: [
            tuple(row)
            for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY id')
        ]
        for table in tables
    }
    for table in tables:
        result[f"{table} columns"] = [
            (row[1], row[2], row[3], row[5])
            for row in connection.execute(f'PRAGMA table_info("{table}")')
        ]
        result[f"{table} keys"] = sorted(
            row[2:5]
            for row in connection.execute(f'PRAGMA foreign_key_list("{table}")')
        )
    connection.close()
    return result


def sql(folder: Path, query: str) -> list[tuple]:
    connection = sqlite3.connect(folder / "phonlab.db")
    try:
        return [tuple(row) for row in connection.execute(query)]
    finally:
        connection.close()


def execute(folder: Path, statement: str) -> None:
    connection = sqlite3.connect(folder / "phonlab.db")
    connection.execute(statement)
    connection.commit()
    connection.close()


# ------------------------------ the same as the app ------------------------------


def test_the_database_is_the_one_the_app_makes(tmp_path: Path):
    by_app, by_library = tmp_path / "app", tmp_path / "library"
    for folder in (by_app, by_library):
        textgrid_project(folder)

    import_with_the_app(by_app)
    import_project(by_library)

    assert dump(by_library) == dump(by_app)


def test_the_database_of_subtitle_files_is_the_one_the_app_makes(tmp_path: Path):
    by_app, by_library = tmp_path / "app", tmp_path / "library"
    for folder in (by_app, by_library):
        write_wavs(folder, ["aa1/aa1_01.wav", "bb2/bb2_01.wav"])
        (folder / "aa1" / "aa1_01.srt").write_text(SRT)
        (folder / "bb2" / "bb2_01.srt").write_text(SRT)

    import_with_the_app(by_app)
    import_project(by_library)

    assert dump(by_library) == dump(by_app)
    # the talkers the file names, and the layout's as the target talker
    assert sql(by_library, "SELECT name FROM talker ORDER BY id") == [
        ("Ann",),
        ("Bob",),
    ]
    assert sql(by_library, "SELECT target_talker FROM recording ORDER BY id") == [
        ("aa1",),
        ("bb2",),
    ]


def test_the_tables_are_made_as_the_app_makes_them(tmp_path: Path):
    by_app = tmp_path / "app"
    by_app.mkdir()
    database = SQLiteDatabase()
    database.connect(str(by_app))
    database.close()
    by_library = tmp_path / "library"
    by_library.mkdir()
    import_project(by_library, strict=False)

    def shapes(folder: Path) -> dict:
        return {k: v for k, v in dump(folder).items() if "columns" in k or "keys" in k}

    assert shapes(by_library) == shapes(by_app)


# --------------------------------- import_project ---------------------------------


def test_a_project_is_read_back_after_it_is_imported(tmp_path: Path):
    textgrid_project(tmp_path)

    result = import_project(tmp_path)

    assert (result.created, result.updated, result.removed) == (4, 0, 0)
    assert len(result.read) == 4
    with open_project(tmp_path) as project:
        assert len(project.recordings()) == 4
        assert project.tier_names() == ["word", "phone"]
        assert project.count_within("word", "phone").n_phone.tolist() == [2, 2] * 4
        assert project.schema_version == schema.SCHEMA_VERSION


def test_the_layout_that_was_inferred_is_saved_with_the_project(tmp_path: Path):
    textgrid_project(tmp_path)

    import_project(tmp_path)

    assert load_layout(str(tmp_path)) is not None


def test_a_layout_that_was_given_is_used_and_saved(tmp_path: Path):
    textgrid_project(tmp_path)
    layout = ProjectLayout(levels=(FolderLevel(1, "group"),))

    import_project(tmp_path, layout)

    assert load_layout(str(tmp_path)) == layout
    with open_project(tmp_path) as project:
        assert set(project.recordings().group) == {"aa1", "bb2"}


def test_a_layout_the_project_has_saved_is_used_and_left_alone(tmp_path: Path):
    textgrid_project(tmp_path)
    saved = ProjectLayout(levels=(FolderLevel(1, "group"),))
    save_layout(str(tmp_path), saved)

    import_project(tmp_path)

    assert load_layout(str(tmp_path)) == saved
    with open_project(tmp_path) as project:
        assert "group" in project.recordings().columns


def test_a_project_that_needs_a_look_is_not_imported_when_strict(tmp_path: Path):
    textgrid_project(tmp_path)
    (tmp_path / "orphan.TextGrid").write_text(word_and_phone_textgrid())

    with pytest.raises(ImportNeedsReview, match="belong to no sound file") as error:
        import_project(tmp_path)

    assert error.value.plan.problems
    assert not (tmp_path / "phonlab.db").exists()
    assert not (tmp_path / "phonlab.toml").exists()


def test_a_project_that_needs_a_look_can_be_imported_anyway(tmp_path: Path):
    textgrid_project(tmp_path)
    (tmp_path / "orphan.TextGrid").write_text(word_and_phone_textgrid())

    result = import_project(tmp_path, strict=False)

    assert result.created == 4
    assert result.plan is not None and result.plan.problems


def test_describing_a_project_writes_nothing(tmp_path: Path):
    textgrid_project(tmp_path)

    plan = describe_project(tmp_path)

    assert plan.problems == []
    assert "4 recordings" in str(plan)
    assert not (tmp_path / "phonlab.db").exists()
    assert not (tmp_path / "phonlab.toml").exists()


def test_importing_again_keeps_the_annotations_it_has(tmp_path: Path):
    textgrid_project(tmp_path)
    import_project(tmp_path)
    execute(tmp_path, "UPDATE annotation_label SET label_text = 'fixed' WHERE id = 1")

    result = import_project(tmp_path)

    assert (result.created, result.updated) == (0, 4)
    assert len(result.kept) == 4 and result.read == []
    assert sql(tmp_path, "SELECT label_text FROM annotation_label WHERE id = 1") == [
        ("fixed",)
    ]


def test_recordings_that_left_the_project_are_removed_unless_annotated(
    tmp_path: Path,
):
    write_wavs(tmp_path, ["a.wav", "b.wav"])
    (tmp_path / "a.TextGrid").write_text(word_and_phone_textgrid())
    import_project(tmp_path)
    (tmp_path / "a.wav").unlink()
    (tmp_path / "a.TextGrid").unlink()
    (tmp_path / "b.wav").unlink()
    write_wavs(tmp_path, ["c.wav"])

    result = import_project(tmp_path, ProjectLayout(annotation_ext=None), strict=False)

    # b had no annotation and went; a has one, so it stays
    assert (result.created, result.removed) == (1, 1)
    assert [r[0] for r in sql(tmp_path, "SELECT file_stem FROM recording")] == [
        "a",
        "c",
    ]


def test_a_file_that_cannot_be_read_is_reported_and_the_rest_imported(
    tmp_path: Path,
):
    textgrid_project(tmp_path)
    (tmp_path / "aa1" / "aa1_01.TextGrid").write_text("this is not a TextGrid")

    result = import_project(tmp_path)

    assert list(result.failed) == ["aa1/aa1_01"]
    assert len(result.read) == 3
    assert sql(tmp_path, "SELECT COUNT(*) FROM annotation_type") == [(6,)]


def test_a_folder_that_does_not_exist_is_not_a_project(tmp_path: Path):
    with pytest.raises(ProjectError, match="is not a folder"):
        import_project(tmp_path / "nowhere")


def test_a_database_another_program_is_writing_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    textgrid_project(tmp_path)
    import_project(tmp_path)
    monkeypatch.setattr(schema, "LOCK_TIMEOUT", 0.05)
    busy = sqlite3.connect(tmp_path / "phonlab.db", isolation_level=None)
    busy.execute("BEGIN EXCLUSIVE")

    try:
        with pytest.raises(ProjectError, match="in use by another program"):
            update_annotations(tmp_path)
    finally:
        busy.close()


def test_a_database_of_a_newer_schema_is_not_written(tmp_path: Path):
    textgrid_project(tmp_path)
    import_project(tmp_path)
    execute(tmp_path, f"PRAGMA user_version = {schema.SCHEMA_VERSION + 1}")

    with pytest.raises(ProjectError, match="newer"):
        update_annotations(tmp_path)


# ---------------------------- add_recordings, update_annotations ----------------------------


def test_new_recordings_are_added_and_the_ones_the_database_has_are_not_touched(
    tmp_path: Path,
):
    textgrid_project(tmp_path)
    import_project(tmp_path)
    execute(tmp_path, "UPDATE annotation_label SET label_text = 'fixed' WHERE id = 1")
    write_wavs(tmp_path, ["aa1/aa1_03.wav"])
    (tmp_path / "aa1" / "aa1_03.TextGrid").write_text(word_and_phone_textgrid())

    result = add_recordings(tmp_path)

    assert (result.created, result.updated, result.read) == (1, 0, ["aa1/aa1_03"])
    assert sql(tmp_path, "SELECT COUNT(*) FROM recording") == [(5,)]
    assert sql(tmp_path, "SELECT label_text FROM annotation_label WHERE id = 1") == [
        ("fixed",)
    ]


def test_adding_recordings_needs_a_database(tmp_path: Path):
    textgrid_project(tmp_path)

    with pytest.raises(ProjectError, match="no project database"):
        add_recordings(tmp_path)


def test_an_annotation_file_that_appears_later_is_read(tmp_path: Path):
    write_wavs(tmp_path, ["a.wav", "b.wav"])
    (tmp_path / "a.TextGrid").write_text(word_and_phone_textgrid())
    import_project(tmp_path)
    (tmp_path / "b.TextGrid").write_text(word_and_phone_textgrid())

    result = update_annotations(tmp_path)

    assert result.read == ["b"] and result.kept == ["a"]
    assert sql(
        tmp_path,
        "SELECT annotation_file FROM recording ORDER BY id",
    ) == [("a.TextGrid",), ("b.TextGrid",)]


def test_annotations_are_replaced_only_when_asked(tmp_path: Path):
    write_wavs(tmp_path, ["a.wav"])
    (tmp_path / "a.TextGrid").write_text(word_and_phone_textgrid())
    import_project(tmp_path)
    execute(tmp_path, "UPDATE annotation_label SET label_text = 'fixed' WHERE id = 1")

    update_annotations(tmp_path)
    assert sql(tmp_path, "SELECT label_text FROM annotation_label WHERE id = 1") == [
        ("fixed",)
    ]

    result = update_annotations(tmp_path, overwrite=True)
    assert result.read == ["a"]
    assert sql(tmp_path, "SELECT label_text FROM annotation_label WHERE id = 1") == [
        ("hi",)
    ]
    assert sql(tmp_path, "SELECT COUNT(*) FROM annotation_type") == [(2,)]


def test_annotations_can_be_updated_for_some_recordings(tmp_path: Path):
    textgrid_project(tmp_path)
    import_project(tmp_path)
    execute(tmp_path, "UPDATE annotation_label SET label_text = 'fixed'")

    result = update_annotations(tmp_path, ["aa1/aa1_01"], overwrite=True)

    assert result.read == ["aa1/aa1_01"]
    texts = {r[0] for r in sql(tmp_path, "SELECT label_text FROM annotation_label")}
    assert texts == {"fixed", "hi", "yo", "h", "i", "y", "o"}


def test_a_recording_the_database_lacks_cannot_be_updated(tmp_path: Path):
    textgrid_project(tmp_path)
    import_project(tmp_path)

    with pytest.raises(ProjectError, match="no recording"):
        update_annotations(tmp_path, ["nope"])


def test_a_file_that_cannot_be_read_leaves_the_annotation_as_it_was(tmp_path: Path):
    write_wavs(tmp_path, ["a.wav"])
    (tmp_path / "a.TextGrid").write_text(word_and_phone_textgrid())
    import_project(tmp_path)
    (tmp_path / "a.TextGrid").write_text("this is not a TextGrid")

    result = update_annotations(tmp_path, overwrite=True)

    assert list(result.failed) == ["a"] and result.read == []
    assert sql(tmp_path, "SELECT COUNT(*) FROM annotation_label") == [(6,)]


CHAT = (
    "@UTF8\n@Begin\n@Participants:\tINV Investigator, PAR Participant\n"
    "*INV:\thow are you ? \x15100_900\x15\n*PAR:\tfine . \x151000_1500\x15\n@End\n"
)


def test_chat_files_give_a_tier_for_each_speaker_whose_talker_is_named_from_the_folders(
    tmp_path: Path,
):
    by_app, by_library = tmp_path / "app", tmp_path / "library"
    layout = ProjectLayout(
        annotation_ext=".cha",
        annotation_dir="Annotation",
        levels=(
            FolderLevel(1, ""),
            FolderLevel(2, "region"),
            FolderLevel(3, "", "{session}-{agegroup}"),
        ),
        filename_template="{gender}_{num}",
        talker_template="{region}_{session}_{agegroup}_{gender}_{num}",
    )
    for folder in (by_app, by_library):
        write_wavs(folder, ["Audio/ATL/se0-ag2/f_01.wav", "Audio/PRV/se0-ag1/m_02.wav"])
        for stem in ("ATL/se0-ag2/f_01", "PRV/se0-ag1/m_02"):
            file = folder / "Annotation" / f"{stem}.cha"
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(CHAT, encoding="utf-8")
        save_layout(str(folder), layout)

    import_with_the_app(by_app)
    import_project(by_library)

    assert dump(by_library) == dump(by_app)
    assert sql(
        by_library,
        "SELECT r.file_stem, t.name, k.name FROM annotation_type AS t "
        "JOIN recording AS r ON r.id = t.annotation_id "
        "JOIN talker AS k ON k.id = t.talker_id ORDER BY r.id, t.id",
    ) == [
        ("Audio/ATL/se0-ag2/f_01", "INV", "INV1"),
        ("Audio/ATL/se0-ag2/f_01", "PAR", "ATL_se0_ag2_f_01"),
        ("Audio/PRV/se0-ag1/m_02", "INV", "INV2"),
        ("Audio/PRV/se0-ag1/m_02", "PAR", "PRV_se0_ag1_m_02"),
    ]
