"""What is written into the project database: recordings (with their talkers, channels
and the files that go with them) and annotations (nodes, tiers and labels). The rules
are those of the desktop app, which makes the same database: a time that two tiers share
is one node, a tier says who produced it only when its source says, and a column the
database lacks is added when a recording first has a value for it."""

import json
import sqlite3
from typing import Any

from core.annotation.entity.annotation import add_node_time
from core.parse_textgrid.parse_textgrid import to_label
from phonlab_project.recording import Recording
from phonlab_project.schema import (
    CHANNEL_TABLE,
    RECORDING_OPTIONAL_COLUMNS,
    add_column,
    table_columns,
)


def recording_ids(connection: sqlite3.Connection) -> dict[str, int]:
    """The id of each recording of the database, by file stem"""
    return {
        stem: id
        for id, stem in connection.execute("SELECT id, file_stem FROM recording")
    }


def upsert_recordings(
    connection: sqlite3.Connection,
    recordings: list[Recording],
    remove_others: bool = True,
) -> tuple[int, int, int]:
    """Make the rows of the recordings what the recordings say: created if the
    database lacks them, else updated, with their talkers and channels. With
    `remove_others`, recordings that are not among them and have no annotation are
    removed. Returns how many were created, updated and removed."""
    created = updated = removed = 0
    ids = recording_ids(connection)
    talkers = {
        name: id for id, name in connection.execute("SELECT id, name FROM talker")
    }
    new_talkers = {
        name for r in recordings for name in [*r.talkers, *r.channel_talkers.values()]
    } - talkers.keys()
    for name in sorted(new_talkers):
        cursor = connection.execute("INSERT INTO talker (name) VALUES (?)", (name,))
        talkers[name] = cursor.lastrowid or 0

    for recording in recordings:
        columns = (
            recording.audio_file,
            recording.annotation_file,
            json.dumps(dict(recording.data_files)),
            json.dumps(dict(recording.fields)),
        )
        if recording.file_stem in ids:
            connection.execute(
                "UPDATE recording SET audio_file = ?, annotation_file = ?, "
                "data_files = ?, fields = ? WHERE id = ?",
                (*columns, ids[recording.file_stem]),
            )
            updated += 1
        else:
            cursor = connection.execute(
                "INSERT INTO recording (file_stem, audio_file, annotation_file, "
                "data_files, fields) VALUES (?, ?, ?, ?, ?)",
                (recording.file_stem, *columns),
            )
            ids[recording.file_stem] = cursor.lastrowid or 0
            created += 1
        _set_links(connection, ids[recording.file_stem], recording, talkers)
        _set_channels(connection, ids[recording.file_stem], recording, talkers)

    if remove_others:
        wanted = {recording.file_stem for recording in recordings}
        for stem, id in ids.items():
            if stem not in wanted and not has_annotation(connection, id):
                _remove_recording(connection, id)
                removed += 1

    _set_optional_columns(connection, recordings)
    return created, updated, removed


def _set_links(
    connection: sqlite3.Connection,
    recording_id: int,
    recording: Recording,
    talkers: dict[str, int],
) -> None:
    names = list(dict.fromkeys(recording.talkers))
    current = [
        row[0]
        for row in connection.execute(
            "SELECT talker.name FROM recording_talker "
            "JOIN talker ON talker.id = recording_talker.talker_id "
            "WHERE recording_id = ? ORDER BY recording_talker.id",
            (recording_id,),
        )
    ]
    if current == names:
        return
    connection.execute(
        "DELETE FROM recording_talker WHERE recording_id = ?", (recording_id,)
    )
    connection.executemany(
        "INSERT INTO recording_talker (recording_id, talker_id) VALUES (?, ?)",
        [(recording_id, talkers[name]) for name in names],
    )


def _set_channels(
    connection: sqlite3.Connection,
    recording_id: int,
    recording: Recording,
    talkers: dict[str, int],
) -> None:
    """The channel rows of a recording stored as a file per channel; the table is made
    when the first such recording is added"""
    if recording.channel_files:
        connection.execute(CHANNEL_TABLE)
    elif not _has_table(connection, "recording_channel"):
        return
    wanted = [
        (channel, audio_file, recording.channel_talkers.get(channel))
        for channel, audio_file in recording.channel_files.items()
    ]
    current = [
        tuple(row)
        for row in connection.execute(
            "SELECT channel, audio_file, talker.name FROM recording_channel "
            "LEFT JOIN talker ON talker.id = recording_channel.talker_id "
            "WHERE recording_id = ? ORDER BY recording_channel.id",
            (recording_id,),
        )
    ]
    if wanted == current:
        return
    connection.execute(
        "DELETE FROM recording_channel WHERE recording_id = ?", (recording_id,)
    )
    connection.executemany(
        "INSERT INTO recording_channel (recording_id, channel, audio_file, talker_id) "
        "VALUES (?, ?, ?, ?)",
        [
            (recording_id, channel, audio_file, talkers.get(talker or ""))
            for channel, audio_file, talker in wanted
        ],
    )


def _set_optional_columns(
    connection: sqlite3.Connection, recordings: list[Recording]
) -> None:
    """Set the video, media offset and target talker of the recordings, adding a column
    to the table first if some recording has a value for it and the table lacks it"""
    present = table_columns(connection, "recording")
    columns = [
        name
        for name in RECORDING_OPTIONAL_COLUMNS
        if name in present or any(getattr(r, name) is not None for r in recordings)
    ]
    for name in columns:
        add_column(connection, "recording", name, RECORDING_OPTIONAL_COLUMNS[name])
    if columns:
        assignments = ", ".join(f'"{name}" = ?' for name in columns)
        connection.executemany(
            f"UPDATE recording SET {assignments} WHERE file_stem = ?",
            [
                (*(getattr(r, name) for name in columns), r.file_stem)
                for r in recordings
            ],
        )


def _remove_recording(connection: sqlite3.Connection, recording_id: int) -> None:
    if _has_table(connection, "recording_channel"):
        connection.execute(
            "DELETE FROM recording_channel WHERE recording_id = ?", (recording_id,)
        )
    connection.execute(
        "DELETE FROM recording_talker WHERE recording_id = ?", (recording_id,)
    )
    connection.execute("DELETE FROM recording WHERE id = ?", (recording_id,))


def _has_table(connection: sqlite3.Connection, name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
        ).fetchone()
        is not None
    )


# -- annotations --


def has_annotation(connection: sqlite3.Connection, recording_id: int) -> bool:
    """Whether the recording has any tiers or nodes"""
    return (
        connection.execute(
            "SELECT EXISTS (SELECT 1 FROM annotation_type WHERE annotation_id = ?) "
            "OR EXISTS (SELECT 1 FROM annotation_node WHERE annotation_id = ?)",
            (recording_id, recording_id),
        ).fetchone()[0]
        == 1
    )


def clear_annotation(connection: sqlite3.Connection, recording_id: int) -> None:
    connection.execute(
        "DELETE FROM annotation_label WHERE annotation_type_id IN "
        "(SELECT id FROM annotation_type WHERE annotation_id = ?)",
        (recording_id,),
    )
    connection.execute(
        "DELETE FROM annotation_type WHERE annotation_id = ?", (recording_id,)
    )
    connection.execute(
        "DELETE FROM annotation_node WHERE annotation_id = ?", (recording_id,)
    )


def write_annotation(
    connection: sqlite3.Connection, recording_id: int, tiers: list[dict[str, Any]]
) -> None:
    """Add the tiers to the (empty) annotation of a recording. `tiers` are as the
    readers give them: dicts with a `name`, `labels` of (begin, end, text) and
    perhaps a `talker`. Times of different tiers that are nearly the same share a
    node. A tier that says who produced it keeps that as its talker."""
    node_times: list[float] = []
    for tier in tiers:
        for begin, end, _ in tier["labels"]:
            node_times = add_node_time(node_times, begin)
            node_times = add_node_time(node_times, end)

    connection.executemany(
        "INSERT INTO annotation_node (annotation_id, time) VALUES (?, ?)",
        [(recording_id, time) for time in node_times],
    )
    nodes = connection.execute(
        "SELECT id, time FROM annotation_node WHERE annotation_id = ? ORDER BY time",
        (recording_id,),
    ).fetchall()
    ids, times = [row[0] for row in nodes], [row[1] for row in nodes]

    talkers: dict[str, str] = {}
    for tier in tiers:
        cursor = connection.execute(
            "INSERT INTO annotation_type (annotation_id, name) VALUES (?, ?)",
            (recording_id, tier["name"]),
        )
        type_id = cursor.lastrowid
        labels = (to_label(times, ids, label) for label in tier["labels"])
        connection.executemany(
            "INSERT INTO annotation_label (annotation_type_id, label_text, "
            "start_node_id, end_node_id) VALUES (?, ?, ?, ?)",
            [(type_id, label.label, label.s_node, label.e_node) for label in labels],
        )
        if tier.get("talker"):
            talkers[tier["name"]] = tier["talker"]
    _set_tier_talkers(connection, recording_id, talkers)


def _set_tier_talkers(
    connection: sqlite3.Connection, recording_id: int, talkers: dict[str, str]
) -> None:
    """Say who produced each tier (tier name -> talker name), adding the talker column
    to the table of tiers the first time any is known, and the talker to the table of
    talkers if it is not there"""
    if not talkers:
        return
    add_column(
        connection,
        "annotation_type",
        "talker_id",
        'INTEGER REFERENCES "talker" ("id")',
    )
    for tier, talker in talkers.items():
        connection.execute(
            "INSERT INTO talker (name) SELECT ? WHERE NOT EXISTS "
            "(SELECT 1 FROM talker WHERE name = ?)",
            (talker, talker),
        )
        connection.execute(
            "UPDATE annotation_type SET talker_id = "
            "(SELECT id FROM talker WHERE name = ?) "
            "WHERE annotation_id = ? AND name = ?",
            (talker, recording_id, tier),
        )
