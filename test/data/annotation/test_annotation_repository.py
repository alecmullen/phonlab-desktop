import shutil
from pathlib import Path

import pytest
from support.audio_files import write_wavs

from core.annotation.entity.annotation import AnnotationLabel, AnnotationType
from core.annotation.entity.metadata import MetadataColumn, MetadataTarget, SqlType
from core.annotation.entity.recording import Recording
from core.parse_textgrid.parse_textgrid import ParseTextGrid
from core.read_tiers.entity.table_format import TierFile
from data.annotation.datasource.annotation_datasource import AnnotationDataSource
from data.annotation.repository.annotation_repository import DataAnnotationRepository
from data.base.database import SQLiteDatabase


@pytest.fixture
def repository(tmp_path: Path) -> DataAnnotationRepository:
    database = SQLiteDatabase()
    database.connect(str(tmp_path))
    yield DataAnnotationRepository(AnnotationDataSource(database))
    database.engine.dispose()


def seeded_annotation(repository: DataAnnotationRepository) -> int:
    """An annotation with nodes at 0, 0.5 and 1 and one type with a label per gap"""
    id = repository.create_annotation("sample")
    nodes = repository.create_nodes(id, [0.0, 0.5, 1.0])
    first, second, third = sorted(nodes, key=nodes.get)
    repository.create_types(
        id,
        [
            AnnotationType(
                "word",
                [
                    AnnotationLabel(first, second, "a"),
                    AnnotationLabel(second, third, "b"),
                ],
            )
        ],
    )
    return id


# --------------------------- annotations ---------------------------


def test_create_annotation_returns_empty_annotation_with_id(
    repository: DataAnnotationRepository,
):
    id = repository.create_annotation("sample")

    annotation = repository.get_annotation_by_id(id)

    assert annotation.id == id
    assert annotation.nodes == {}
    assert annotation.types == []


def test_create_annotation_raises_for_duplicate_file_stem(
    repository: DataAnnotationRepository,
):
    repository.create_annotation("sample")

    with pytest.raises(ValueError):
        repository.create_annotation("sample")


def test_get_annotation_by_id_raises_for_unknown_id(
    repository: DataAnnotationRepository,
):
    with pytest.raises(ValueError):
        repository.get_annotation_by_id(99)


def test_find_annotation_by_file_stem_returns_none_when_missing(
    repository: DataAnnotationRepository,
):
    assert repository.find_annotation_by_file_stem("missing") is None


def test_find_annotation_by_file_stem_returns_stored_annotation(
    repository: DataAnnotationRepository,
):
    id = seeded_annotation(repository)

    annotation = repository.find_annotation_by_file_stem("sample")

    assert annotation is not None
    assert annotation.id == id
    assert sorted(annotation.nodes.values()) == [0.0, 0.5, 1.0]
    assert [t.type for t in annotation.types] == ["word"]
    assert [label.label for label in annotation.types[0].labels] == ["a", "b"]


# --------------------------- nodes ---------------------------


def test_create_node_adds_new_node(repository: DataAnnotationRepository):
    id = repository.create_annotation("sample")

    node_id, time = repository.create_node(id, 0.25)

    assert time == 0.25
    assert repository.get_annotation_by_id(id).nodes == {node_id: 0.25}


def test_create_node_reuses_node_within_threshold(
    repository: DataAnnotationRepository,
):
    id = repository.create_annotation("sample")
    node_id, _ = repository.create_node(id, 0.25)

    same_id, same_time = repository.create_node(id, 0.251, same_threshold=0.01)

    assert same_id == node_id
    assert same_time == 0.25
    assert len(repository.get_annotation_by_id(id).nodes) == 1


def test_create_nodes_merges_nodes_within_threshold(
    repository: DataAnnotationRepository,
):
    id = repository.create_annotation("sample")
    repository.create_nodes(id, [0.0, 1.0])

    created = repository.create_nodes(id, [0.001, 0.5], same_threshold=0.01)

    assert sorted(created.values()) == [0.0, 0.5]
    assert len(repository.get_annotation_by_id(id).nodes) == 3


def test_update_node_changes_time(repository: DataAnnotationRepository):
    id = repository.create_annotation("sample")
    node_id, _ = repository.create_node(id, 0.25)

    repository.update_node(node_id, 0.75)

    assert repository.get_annotation_by_id(id).nodes[node_id] == 0.75


def test_delete_node_removes_node(repository: DataAnnotationRepository):
    id = repository.create_annotation("sample")
    node_id, _ = repository.create_node(id, 0.25)

    repository.delete_node(node_id)

    assert repository.get_annotation_by_id(id).nodes == {}


def test_delete_nodes_if_no_labels_keeps_nodes_used_by_labels(
    repository: DataAnnotationRepository,
):
    id = seeded_annotation(repository)
    annotation = repository.get_annotation_by_id(id)
    used = {
        n for label in annotation.types[0].labels for n in (label.s_node, label.e_node)
    }
    unused_id, _ = repository.create_node(id, 5.0)

    deleted = repository.delete_nodes_if_no_labels([*used, unused_id])

    assert deleted == [unused_id]
    assert set(repository.get_annotation_by_id(id).nodes) == used


# --------------------------- labels ---------------------------


def test_create_label_returns_label_with_id(repository: DataAnnotationRepository):
    id = seeded_annotation(repository)
    annotation = repository.get_annotation_by_id(id)
    type_id = annotation.types[0].id
    start, end = sorted(annotation.nodes)[:2]

    label = repository.create_label(AnnotationLabel(start, end, "new"), type_id)

    assert label.id is not None
    assert label.label == "new"
    labels = repository.get_annotation_by_id(id).types[0].labels
    assert "new" in [stored.label for stored in labels]


def test_update_label_changes_text(repository: DataAnnotationRepository):
    id = seeded_annotation(repository)
    label = repository.get_annotation_by_id(id).types[0].labels[0]

    repository.update_label(
        AnnotationLabel(label.s_node, label.e_node, "changed", label.id)
    )

    labels = repository.get_annotation_by_id(id).types[0].labels
    assert [stored.label for stored in labels if stored.id == label.id] == ["changed"]


def test_delete_label_removes_label(repository: DataAnnotationRepository):
    id = seeded_annotation(repository)
    label = repository.get_annotation_by_id(id).types[0].labels[0]

    repository.delete_label(label)

    labels = repository.get_annotation_by_id(id).types[0].labels
    assert label.id not in [stored.id for stored in labels]
    assert len(labels) == 1


# --------------------------- file stems ---------------------------


def test_create_annotations_if_missing_adds_empty_annotation_per_stem(
    repository: DataAnnotationRepository,
):
    repository.create_annotations_if_missing(["a", "b"])

    for stem in ("a", "b"):
        annotation = repository.find_annotation_by_file_stem(stem)
        assert annotation is not None
        assert annotation.nodes == {}
        assert annotation.types == []


def test_create_annotations_if_missing_keeps_existing_annotation(
    repository: DataAnnotationRepository,
):
    id = seeded_annotation(repository)

    repository.create_annotations_if_missing(["sample", "other"])

    kept = repository.get_annotation_by_id(id)
    assert len(kept.nodes) == 3
    assert [type.type for type in kept.types] == ["word"]
    assert repository.find_annotation_by_file_stem("other") is not None


def test_create_annotations_if_missing_is_idempotent_and_ignores_duplicates(
    repository: DataAnnotationRepository,
):
    repository.create_annotations_if_missing(["a", "a"])
    first = repository.find_annotation_by_file_stem("a")

    repository.create_annotations_if_missing(["a"])

    assert repository.find_annotation_by_file_stem("a") == first


def test_create_annotations_if_missing_accepts_no_stems(
    repository: DataAnnotationRepository,
):
    repository.create_annotations_if_missing([])


def test_clear_annotation_removes_nodes_and_types_but_keeps_stem(
    repository: DataAnnotationRepository,
):
    id = seeded_annotation(repository)

    repository.clear_annotation(id)

    cleared = repository.get_annotation_by_id(id)
    assert cleared.nodes == {}
    assert cleared.types == []
    assert repository.find_annotation_by_file_stem("sample") is not None


def test_clear_annotation_leaves_other_annotations_alone(
    repository: DataAnnotationRepository,
):
    id = seeded_annotation(repository)
    other = repository.create_annotation("other")
    repository.create_nodes(other, [0.0, 1.0])

    repository.clear_annotation(id)

    assert len(repository.get_annotation_by_id(other).nodes) == 2


def test_clear_annotation_raises_for_unknown_id(repository: DataAnnotationRepository):
    with pytest.raises(ValueError):
        repository.clear_annotation(999)


# --------------------------- reset ---------------------------


def test_reset_backs_up_the_database_and_starts_an_empty_one(
    repository: DataAnnotationRepository, tmp_path: Path
):
    seeded_annotation(repository)

    backup = repository.reset()

    assert backup is not None
    assert Path(backup).is_file()
    assert Path(backup).parent == tmp_path
    assert (tmp_path / "phonlab.db").is_file()
    assert repository.find_annotation_by_file_stem("sample") is None


def test_repository_keeps_working_after_reset(repository: DataAnnotationRepository):
    seeded_annotation(repository)
    repository.reset()

    id = seeded_annotation(repository)

    assert len(repository.get_annotation_by_id(id).nodes) == 3


def test_backup_still_holds_the_old_annotations(
    repository: DataAnnotationRepository, tmp_path: Path
):
    seeded_annotation(repository)
    backup = repository.reset()
    assert backup is not None
    restored_dir = tmp_path / "restored"
    restored_dir.mkdir()
    shutil.copy(backup, restored_dir / "phonlab.db")

    restored = SQLiteDatabase()
    restored.connect(str(restored_dir))
    try:
        old = DataAnnotationRepository(AnnotationDataSource(restored))
        assert old.find_annotation_by_file_stem("sample") is not None
    finally:
        restored.engine.dispose()


def test_two_resets_make_two_backups(
    repository: DataAnnotationRepository, tmp_path: Path
):
    first = repository.reset()
    second = repository.reset()

    assert first != second
    assert len(list(tmp_path.glob("*.bak"))) == 2


# --------------------------- tier names ---------------------------


def test_list_tier_names_is_empty_for_an_empty_database(
    repository: DataAnnotationRepository,
):
    assert repository.list_tier_names() == []


def test_list_tier_names_has_each_name_once_across_annotations_sorted(
    repository: DataAnnotationRepository,
):
    first, second = repository.create_annotation("a"), repository.create_annotation("b")
    repository.create_types(
        first, [AnnotationType("word", []), AnnotationType("Break", [])]
    )
    repository.create_types(
        second, [AnnotationType("word", []), AnnotationType("phone", [])]
    )

    assert repository.list_tier_names() == ["Break", "phone", "word"]


def test_list_tier_names_includes_tiers_that_have_labels(
    repository: DataAnnotationRepository,
):
    seeded_annotation(repository)  # a "word" tier with labels

    assert repository.list_tier_names() == ["word"]


# --------------------------- tier label search ---------------------------


def test_find_labels_by_tier_name_returns_labels_with_file_and_times(
    repository: DataAnnotationRepository,
):
    seeded_annotation(repository)

    found = repository.find_labels_by_tier_name("word")

    assert sorted((l.file_stem, l.label.label, l.start, l.end) for l in found) == [
        ("sample", "a", 0.0, 0.5),
        ("sample", "b", 0.5, 1.0),
    ]
    assert all(l.tier_name == "word" and l.label.id is not None for l in found)


def test_find_labels_by_tier_name_spans_files_and_can_be_limited_to_one(
    repository: DataAnnotationRepository,
):
    seeded_annotation(repository)
    other = repository.create_annotation("other")
    nodes = repository.create_nodes(other, [0.0, 2.0])
    start, end = sorted(nodes, key=nodes.get)
    repository.create_types(
        other, [AnnotationType("word", [AnnotationLabel(start, end, "c")])]
    )

    everywhere = repository.find_labels_by_tier_name("word")
    one_file = repository.find_labels_by_tier_name("word", "other")

    assert sorted(l.label.label for l in everywhere) == ["a", "b", "c"]
    assert [(l.file_stem, l.label.label) for l in one_file] == [("other", "c")]


def test_find_labels_by_tier_name_ignores_other_tiers(
    repository: DataAnnotationRepository,
):
    seeded_annotation(repository)

    assert repository.find_labels_by_tier_name("phone") == []


# --------------------------- close ---------------------------


def test_repository_keeps_working_after_close(repository: DataAnnotationRepository):
    id = seeded_annotation(repository)

    repository.close()

    assert len(repository.get_annotation_by_id(id).nodes) == 3


# --------------------------- recordings ---------------------------


def test_upsert_recordings_stores_files_talkers_and_fields(
    repository: DataAnnotationRepository,
):
    recording = Recording(
        "t1/a",
        audio_file="t1/a.wav",
        annotation_file="t1/a.TextGrid",
        video_file="t1/a.mp4",
        media_offset=0.25,
        target_talker="t1",
        data_files={"track": "t1/a.trk"},
        talkers=["t1", "t2"],
        fields={"dialect": "north"},
    )

    result = repository.upsert_recordings([recording])

    assert (result.created, result.updated, result.removed) == (1, 0, 0)
    assert repository.list_recordings() == [recording]


def test_the_media_columns_are_added_only_when_a_recording_has_a_value(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings([Recording("a", audio_file="a.wav")])
    assert "video_file" not in repository.read_table("recording", 10).columns
    assert "media_offset" not in repository.read_table("recording", 10).columns

    repository.upsert_recordings(
        [Recording("a", audio_file="a.wav", media_offset=0.5), Recording("b")]
    )

    columns = repository.read_table("recording", 10).columns
    assert "media_offset" in columns
    assert "video_file" not in columns  # nothing had a video
    assert [r.media_offset for r in repository.list_recordings()] == [0.5, None]


def test_the_target_talker_column_is_added_only_when_a_recording_has_one(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings([Recording("a", talkers=["Ann"])])
    assert "target_talker" not in repository.read_table("recording", 10).columns

    repository.upsert_recordings(
        [Recording("a", talkers=["Ann"], target_talker="aa1"), Recording("b")]
    )

    assert "target_talker" in repository.read_table("recording", 10).columns
    assert [r.target_talker for r in repository.list_recordings()] == ["aa1", None]
    assert repository.list_recordings()[0].talkers == ["Ann"]
    assert "target_talker" in repository.builtin_columns(MetadataTarget.RECORDING)


def test_media_values_are_replaced_and_cleared_when_the_recording_is_imported_again(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings([Recording("a", video_file="a.mp4")])

    repository.upsert_recordings([Recording("a", video_file="b.mp4")])
    assert repository.list_recordings()[0].video_file == "b.mp4"

    repository.upsert_recordings([Recording("a")])
    assert repository.list_recordings()[0].video_file is None


def test_media_columns_are_not_taken_for_columns_the_user_added(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings([Recording("a", video_file="a.mp4")])

    assert "video_file" in repository.builtin_columns(MetadataTarget.RECORDING)
    assert repository.read_metadata(MetadataTarget.RECORDING) == {}


def test_upsert_recordings_updates_existing_rows_and_keeps_their_annotation(
    repository: DataAnnotationRepository,
):
    id = seeded_annotation(repository)
    repository.upsert_recordings([Recording("sample", audio_file="sample.wav")])
    result = repository.upsert_recordings(
        [Recording("sample", audio_file="sample.wav", talkers=["x"])]
    )

    assert (result.created, result.updated) == (0, 1)
    assert repository.list_recordings()[0].talkers == ["x"]
    assert len(repository.get_annotation_by_id(id).types[0].labels) == 2


def test_upsert_recordings_removes_rows_without_annotation_that_are_gone(
    repository: DataAnnotationRepository,
):
    seeded_annotation(repository)  # has a type, so it stays
    repository.upsert_recordings([Recording("a"), Recording("b")])

    result = repository.upsert_recordings([Recording("a")])

    assert result.removed == 1
    assert [r.file_stem for r in repository.list_recordings()] == ["a", "sample"]


def test_annotation_rows_created_without_import_have_empty_recording_info(
    repository: DataAnnotationRepository,
):
    repository.create_annotation("plain")

    [recording] = repository.list_recordings()

    assert recording == Recording("plain")


def test_channel_files_and_talkers_are_stored(repository: DataAnnotationRepository):
    recording = Recording(
        "a",
        audio_file="a_L.wav",
        channel_files={"L": "a_L.wav", "R": "a_R.wav"},
        channel_talkers={"L": "Ann", "R": "Bob"},
        talkers=["Ann", "Bob"],
    )

    repository.upsert_recordings([recording])

    assert repository.list_recordings() == [recording]


# --------------------------- talkers and added information ---------------------------


def test_upsert_recordings_makes_a_row_for_each_talker(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings(
        [
            Recording("a", talkers=["Ann", "Bob"]),
            Recording("b", talkers=["Ann"]),
        ]
    )

    assert repository.list_talkers() == ["Ann", "Bob"]


def test_columns_can_be_added_to_a_table_that_has_rows(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings([Recording("a", talkers=["Ann"]), Recording("b")])

    updated = repository.add_metadata(
        MetadataTarget.RECORDING,
        [MetadataColumn("speech_rate", SqlType.REAL), MetadataColumn("cond")],
        {"a": {"speech_rate": 4.5, "cond": "slow"}, "missing": {"cond": "x"}},
    )

    assert updated == 1  # "missing" names no recording
    assert repository.read_metadata(MetadataTarget.RECORDING) == {
        "a": {"speech_rate": 4.5, "cond": "slow"},
        "b": {"speech_rate": None, "cond": None},
    }
    assert repository.list_recordings()[0].file_stem == "a"  # ordinary reads still work


def test_talker_information_goes_in_the_talker_table(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings([Recording("a", talkers=["Ann", "Bob"])])

    repository.add_metadata(
        MetadataTarget.TALKER,
        [MetadataColumn("age", SqlType.INTEGER)],
        {"Ann": {"age": 31}},
    )

    assert repository.read_metadata(MetadataTarget.TALKER) == {
        "Ann": {"age": 31},
        "Bob": {"age": None},
    }


def test_adding_the_same_column_again_updates_its_values(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings([Recording("a")])
    column = [MetadataColumn("rate", SqlType.REAL)]
    repository.add_metadata(MetadataTarget.RECORDING, column, {"a": {"rate": 1.0}})

    repository.add_metadata(MetadataTarget.RECORDING, column, {"a": {"rate": 2.0}})

    assert repository.read_metadata(MetadataTarget.RECORDING) == {"a": {"rate": 2.0}}


def test_added_columns_survive_importing_the_recordings_again(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings([Recording("a")])
    repository.add_metadata(
        MetadataTarget.RECORDING,
        [MetadataColumn("rate", SqlType.REAL)],
        {"a": {"rate": 3.0}},
    )

    repository.upsert_recordings([Recording("a", talkers=["Ann"])])

    assert repository.read_metadata(MetadataTarget.RECORDING) == {"a": {"rate": 3.0}}


def test_unsafe_column_names_are_refused(repository: DataAnnotationRepository):
    with pytest.raises(ValueError):
        repository.add_metadata(
            MetadataTarget.RECORDING,
            [MetadataColumn('x"; DROP TABLE annotation; --')],
            {},
        )


def test_builtin_columns_are_not_reported_as_added_information(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings([Recording("a")])

    assert repository.read_metadata(MetadataTarget.RECORDING) == {}
    assert "file_stem" in repository.builtin_columns(MetadataTarget.RECORDING)
    assert repository.builtin_columns(MetadataTarget.TALKER) == ["id", "name"]


# --------------------------- looking at tables ---------------------------


def test_tables_list_puts_recordings_and_talkers_first(
    repository: DataAnnotationRepository,
):
    assert repository.list_tables()[:3] == ["recording", "talker", "recording_talker"]


def test_read_table_returns_columns_including_added_ones(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings([Recording("a"), Recording("b"), Recording("c")])
    repository.add_metadata(
        MetadataTarget.RECORDING,
        [MetadataColumn("rate", SqlType.REAL)],
        {"a": {"rate": 2.5}},
    )

    data = repository.read_table("recording", 2)

    assert data.n_rows == 3
    assert len(data.rows) == 2
    assert data.columns[-1] == "rate"
    assert data.rows[0][data.columns.index("file_stem")] == "a"
    assert data.rows[0][-1] == 2.5


def test_times_are_shown_with_three_places_wherever_they_appear(
    repository: DataAnnotationRepository,
):
    seeded_annotation(repository)

    nodes = table_rows(repository, "annotation_node")
    labels = table_rows(repository, "annotation_label")

    assert [row["time"] for row in nodes] == ["0.000", "0.500", "1.000"]
    assert {row["start_node"] for row in labels} <= {"0.000", "0.500", "1.000"}
    assert all(isinstance(row["end_node"], str) for row in labels)


def test_read_table_refuses_names_that_are_not_tables(
    repository: DataAnnotationRepository,
):
    with pytest.raises(ValueError):
        repository.read_table('recording"; DROP TABLE recording; --', 10)


# --------------------------- talkers and channels in their own tables ---------------------------


def table_rows(repository: DataAnnotationRepository, name: str) -> list[dict]:
    data = repository.read_table(name, 1000)
    return [dict(zip(data.columns, row)) for row in data.rows]


def test_the_recording_table_has_no_columns_for_talkers_or_channels(
    repository: DataAnnotationRepository,
):
    data = repository.read_table("recording", 10)

    assert data.columns == [
        "id",
        "file_stem",
        "audio_file",
        "annotation_file",
        "data_files",
        "fields",
    ]


def test_talkers_of_a_recording_are_linked_not_listed(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings(
        [Recording("a", talkers=["Ann", "Bob"]), Recording("b", talkers=["Bob"])]
    )

    rows = table_rows(repository, "recording_talker")

    assert [(r["recording"], r["talker"]) for r in rows] == [
        ("a", "Ann"),
        ("a", "Bob"),
        ("b", "Bob"),
    ]
    assert repository.list_recordings()[0].talkers == ["Ann", "Bob"]


def test_a_talker_is_one_row_however_many_recordings_it_is_in(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings(
        [Recording("a", talkers=["Ann"]), Recording("b", talkers=["Ann"])]
    )

    assert repository.list_talkers() == ["Ann"]


def test_adding_recordings_again_replaces_the_talkers_of_each(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings([Recording("a", talkers=["Ann", "Bob"])])

    repository.upsert_recordings([Recording("a", talkers=["Bob", "Ann", "Bob"])])

    assert repository.list_recordings()[0].talkers == ["Bob", "Ann"]
    assert len(table_rows(repository, "recording_talker")) == 2


def test_channels_have_their_own_table_with_the_talker_on_each(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings(
        [
            Recording(
                "a",
                audio_file="a_L.wav",
                channel_files={"L": "a_L.wav", "R": "a_R.wav"},
                channel_talkers={"L": "Ann"},
                talkers=["Ann"],
            ),
            Recording("b", audio_file="b.wav"),
        ]
    )

    rows = table_rows(repository, "recording_channel")

    assert [
        (r["recording"], r["channel"], r["audio_file"], r["talker"]) for r in rows
    ] == [
        ("a", "L", "a_L.wav", "Ann"),
        ("a", "R", "a_R.wav", None),
    ]


def test_a_channel_talker_not_listed_among_the_talkers_still_gets_a_row(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings(
        [
            Recording(
                "a",
                channel_files={"L": "a_L.wav"},
                channel_talkers={"L": "Ann"},
            )
        ]
    )

    assert repository.list_talkers() == ["Ann"]
    assert repository.list_recordings()[0].channel_talkers == {"L": "Ann"}


def test_recordings_that_leave_the_project_take_their_links_with_them(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings(
        [
            Recording("a", talkers=["Ann"], channel_files={"L": "a.wav"}),
            Recording("b", talkers=["Bob"]),
        ]
    )

    repository.upsert_recordings([Recording("b", talkers=["Bob"])])

    assert [r["recording"] for r in table_rows(repository, "recording_talker")] == ["b"]
    assert table_rows(repository, "recording_channel") == []


def test_there_is_no_channel_table_until_a_recording_has_channel_files(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings([Recording("a", audio_file="a.wav")])

    assert "recording_channel" not in repository.list_tables()
    assert repository.list_recordings()[0].channel_files == {}
    with pytest.raises(ValueError):
        repository.read_table("recording_channel", 10)

    repository.upsert_recordings(
        [Recording("a", channel_files={"L": "a_L.wav", "R": "a_R.wav"})]
    )

    assert "recording_channel" in repository.list_tables()
    assert repository.list_recordings()[0].channel_files == {
        "L": "a_L.wav",
        "R": "a_R.wav",
    }


def test_channel_rows_follow_the_recording_when_its_channels_change(
    repository: DataAnnotationRepository,
):
    repository.upsert_recordings([Recording("a", channel_files={"L": "a_L.wav"})])

    repository.upsert_recordings(
        [Recording("a", channel_files={"L": "a_L.wav", "R": "a_R.wav"})]
    )
    assert [r["channel"] for r in table_rows(repository, "recording_channel")] == [
        "L",
        "R",
    ]

    repository.upsert_recordings([Recording("a", audio_file="a.wav")])
    assert table_rows(repository, "recording_channel") == []


# --------------------------- tables read with names instead of ids ---------------------------


def test_annotation_tables_show_names_and_times_not_ids(
    repository: DataAnnotationRepository,
):
    seeded_annotation(repository)

    types = table_rows(repository, "annotation_type")
    labels = table_rows(repository, "annotation_label")
    nodes = table_rows(repository, "annotation_node")

    assert [(r["recording"], r["name"]) for r in types] == [("sample", "word")]
    assert [(r["annotation_type"], r["label_text"]) for r in labels] == [
        ("word", "a"),
        ("word", "b"),
    ]
    assert [(r["start_node"], r["end_node"]) for r in labels] == [
        ("0.000", "0.500"),
        ("0.500", "1.000"),
    ]
    assert {r["recording"] for r in nodes} == {"sample"}
    assert sorted(r["time"] for r in nodes) == ["0.000", "0.500", "1.000"]


def test_a_row_of_the_table_itself_keeps_its_own_id(
    repository: DataAnnotationRepository,
):
    seeded_annotation(repository)

    assert [r["id"] for r in table_rows(repository, "annotation_label")] == [1, 2]


# --------------------------- tiers read from text tables ---------------------------


def test_times_of_a_table_in_milliseconds_are_stored_in_seconds(
    repository: DataAnnotationRepository, tmp_path: Path
):
    write_wavs(tmp_path, ["a.wav"], frames=20000, fs=8000)  # 2.5 s
    table = tmp_path / "a_phn.txt"
    table.write_text("0 400 h\n400 2500 ay\n")
    ParseTextGrid(repository).run_sync(
        None,
        "a",
        tier_files={"Phone": TierFile(str(table))},
        audio_path=str(tmp_path / "a.wav"),
    )

    annotation = repository.find_annotation_by_file_stem("a")

    assert annotation is not None
    assert sorted(annotation.nodes.values()) == [0.0, 0.4, 2.5]


# --------------------------- the word table ---------------------------


def test_the_labels_of_a_tier_are_counted_by_their_text(
    repository: DataAnnotationRepository,
):
    seeded_annotation(repository)  # tier "word" with the labels a and b

    counts = repository.tier_label_counts("word")

    assert counts == {"a": 1, "b": 1}
    assert repository.tier_label_counts("nothing") == {}


def test_a_database_has_no_word_table_until_words_are_added(
    repository: DataAnnotationRepository,
):
    assert "word" not in repository.list_tables()

    repository.replace_words([], [("the", {})])

    assert "word" in repository.list_tables()


def test_the_word_table_has_the_columns_and_rows_of_the_table(
    repository: DataAnnotationRepository,
):
    columns = [MetadataColumn("freq", SqlType.REAL), MetadataColumn("pos")]

    written = repository.replace_words(
        columns, [("the", {"freq": 61.3, "pos": "det"}), ("cat", {"freq": None})]
    )

    data = repository.read_table("word", 10)
    assert written == 2
    assert data.columns == ["id", "word", "freq", "pos"]
    assert [row[1:] for row in data.rows] == [
        ["the", 61.3, "det"],
        ["cat", None, None],
    ]


def test_adding_words_again_replaces_the_word_table(
    repository: DataAnnotationRepository,
):
    repository.replace_words([MetadataColumn("old")], [("a", {"old": "1"})])

    repository.replace_words([MetadataColumn("new")], [("b", {"new": "2"})])

    data = repository.read_table("word", 10)
    assert data.columns == ["id", "word", "new"]
    assert [row[1:] for row in data.rows] == [["b", "2"]]


def test_a_column_name_that_is_not_safe_is_refused(
    repository: DataAnnotationRepository,
):
    with pytest.raises(ValueError):
        repository.replace_words([MetadataColumn('x"; DROP TABLE talker; --')], [])


# --------------------------- the talker of a tier ---------------------------


def test_a_tier_remembers_its_talker_and_the_talker_is_in_the_talker_table(
    repository: DataAnnotationRepository,
):
    id = repository.create_annotation("a")
    repository.create_types(
        id,
        [
            AnnotationType("a-words", [], talker="ann"),
            AnnotationType("b-words", [], talker="bob"),
            AnnotationType("notes", []),
        ],
    )

    annotation = repository.get_annotation_by_id(id)

    assert [type.talker for type in annotation.types] == ["ann", "bob", None]
    assert repository.list_talkers() == ["ann", "bob"]
    found = repository.find_annotation_by_file_stem("a")
    assert found is not None and [t.talker for t in found.types] == ["ann", "bob", None]


def test_the_talker_column_of_tiers_is_only_added_when_a_tier_has_a_talker(
    repository: DataAnnotationRepository,
):
    id = repository.create_annotation("a")
    repository.create_types(id, [AnnotationType("words", [])])
    assert "talker" not in repository.read_table("annotation_type", 10).columns

    other = repository.create_annotation("b")
    repository.create_types(other, [AnnotationType("words", [], talker="ann")])

    assert "talker" in repository.read_table("annotation_type", 10).columns
    assert repository.get_annotation_by_id(id).types[0].talker is None


def test_the_talker_of_a_tier_is_shown_by_name_when_the_table_is_read(
    repository: DataAnnotationRepository,
):
    id = repository.create_annotation("a")
    repository.create_types(id, [AnnotationType("words", [], talker="ann")])

    data = repository.read_table("annotation_type", 10)

    assert data.rows[0][data.columns.index("talker")] == "ann"
