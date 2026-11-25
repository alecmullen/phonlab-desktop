import re
from collections import Counter
from typing import Any

from sqlalchemy import Row, delete, exists, func, inspect, or_, select, text
from sqlalchemy.orm import Session, aliased, selectinload

from core.annotation.entity.metadata import MetadataColumn, MetadataTarget
from core.annotation.entity.recording import Recording, RecordingUpsertResult
from core.inspect_database.entity.table_data import TableData
from data.annotation.entity.annotation import AnnotationEntity
from data.annotation.entity.annotation_label import AnnotationLabelEntity
from data.annotation.entity.annotation_node import AnnotationNodeEntity
from data.annotation.entity.annotation_type import AnnotationTypeEntity
from data.annotation.entity.recording_channel import RecordingChannelEntity
from data.annotation.entity.recording_talker import RecordingTalkerEntity
from data.annotation.entity.talker import TalkerEntity
from data.annotation.entity.word import WordEntity
from data.annotation.mapping.annotation_mapping import set_recording_columns
from data.base.base_entity import BaseEntity
from data.base.datasource import DataSource

SAFE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# Columns of the recording table that are only added when a recording has a value for
# them, as most projects have none: name -> SQL type
RECORDING_OPTIONAL_COLUMNS = {
    "video_file": "TEXT",
    "media_offset": "REAL",
    "target_talker": "TEXT",
}

# what added information is about -> (table entity, column that identifies a row)
METADATA_TABLES: dict[MetadataTarget, tuple[type[BaseEntity], str, str]] = {
    MetadataTarget.RECORDING: (AnnotationEntity, "recording", "file_stem"),
    MetadataTarget.TALKER: (TalkerEntity, "talker", "name"),
}


# When a table is read to be looked at, a column that points at a row of one of these
# tables shows this column of that row instead of the row's number
READABLE_COLUMN = {
    "recording": "file_stem",
    "talker": "name",
    "annotation_type": "name",
    "annotation_node": "time",
}
NODE_TABLE = "annotation_node"  # its times are shown with three places


def _three_places(value: str) -> str:
    """SQL for a time `value` as text with three places after the decimal point"""
    return f"CASE WHEN {value} IS NULL THEN NULL ELSE printf('%.3f', {value}) END"


FIRST_TABLES = ("recording", "talker", "recording_talker", "recording_channel")


class AnnotationDataSource(DataSource):
    def find_annotation_by_file_stem(self, file_stem: str) -> AnnotationEntity | None:
        with self.database.open_session() as session:
            stmt = (
                select(AnnotationEntity)
                .where(AnnotationEntity.file_stem == file_stem)
                .options(
                    selectinload(AnnotationEntity.nodes),
                    selectinload(AnnotationEntity.types).selectinload(
                        AnnotationTypeEntity.labels
                    ),
                )
            )
            annotation = session.scalar(stmt)

        return annotation

    def find_labels_by_tier_name(
        self, tier_name: str, file_stem: str | None = None
    ) -> list[Row]:
        """Rows of (file_stem, tier name, label id, label text, start node id,
        end node id, start time, end time) for every label on tiers with this name"""
        start_node = aliased(AnnotationNodeEntity)
        end_node = aliased(AnnotationNodeEntity)
        stmt = (
            select(
                AnnotationEntity.file_stem,
                AnnotationTypeEntity.name,
                AnnotationLabelEntity.id,
                AnnotationLabelEntity.label_text,
                AnnotationLabelEntity.start_node_id,
                AnnotationLabelEntity.end_node_id,
                start_node.time,
                end_node.time,
            )
            .join(
                AnnotationTypeEntity,
                AnnotationTypeEntity.annotation_id == AnnotationEntity.id,
            )
            .join(
                AnnotationLabelEntity,
                AnnotationLabelEntity.annotation_type_id == AnnotationTypeEntity.id,
            )
            .join(start_node, start_node.id == AnnotationLabelEntity.start_node_id)
            .join(end_node, end_node.id == AnnotationLabelEntity.end_node_id)
            .where(AnnotationTypeEntity.name == tier_name)
        )
        if file_stem is not None:
            stmt = stmt.where(AnnotationEntity.file_stem == file_stem)

        with self.database.open_session() as session:
            return list(session.execute(stmt).all())

    def get_annotation_by_id(self, id: int) -> AnnotationEntity:
        with self.database.open_session() as session:
            stmt = (
                select(AnnotationEntity)
                .where(AnnotationEntity.id == id)
                .options(
                    selectinload(AnnotationEntity.nodes),
                    selectinload(AnnotationEntity.types).selectinload(
                        AnnotationTypeEntity.labels
                    ),
                )
            )
            annotation = session.scalar(stmt)

        if annotation is None:
            raise ValueError("Annotation with that id does not exist in database")

        return annotation

    def add_annotation(self, annotation: AnnotationEntity) -> int:
        with self.database.open_session() as session:
            session.add(annotation)
            session.flush()
            id = annotation.id
            session.commit()

        return id

    def add_annotations_if_missing(self, file_stems: list[str]):
        with self.database.open_session() as session:
            existing = set(
                session.scalars(
                    select(AnnotationEntity.file_stem).where(
                        AnnotationEntity.file_stem.in_(file_stems)
                    )
                )
            )
            session.add_all(
                AnnotationEntity(file_stem=stem)
                for stem in dict.fromkeys(file_stems)
                if stem not in existing
            )
            session.commit()

    def reset(self) -> str | None:
        return self.database.reset()

    def close(self):
        self.database.close()

    def clear_annotation(self, annotation_id: int):
        with self.database.open_session() as session:
            annotation = session.get(AnnotationEntity, annotation_id)
            if annotation is None:
                raise ValueError("Annotation with that id does not exist in database")
            annotation.types.clear()
            annotation.nodes.clear()
            session.commit()

    def list_tier_names(self) -> list[str]:
        with self.database.open_session() as session:
            stmt = select(AnnotationTypeEntity.name).distinct()
            names = list(session.scalars(stmt))

        return sorted(names, key=lambda name: (name.casefold(), name))

    def find_node_by_time(
        self, annotation_id: int, time: float, threshold: float
    ) -> AnnotationNodeEntity | None:
        with self.database.open_session() as session:
            stmt = (
                select(AnnotationNodeEntity)
                .where(AnnotationNodeEntity.annotation_id == annotation_id)
                .where(
                    AnnotationNodeEntity.time.between(
                        time - threshold, time + threshold
                    )
                )
            )

            node = session.scalar(stmt)

        return node

    def list_nodes(self, annotation_id: int) -> list[AnnotationNodeEntity]:
        """The nodes of an annotation, in time order"""
        with self.database.open_session() as session:
            stmt = (
                select(AnnotationNodeEntity)
                .where(AnnotationNodeEntity.annotation_id == annotation_id)
                .order_by(AnnotationNodeEntity.time)
            )
            return list(session.scalars(stmt))

    def add_node(self, node: AnnotationNodeEntity) -> AnnotationNodeEntity:
        with self.database.open_session() as session:
            session.add(node)
            session.commit()
            session.refresh(node)
        return node

    def add_nodes(
        self, nodes: list[AnnotationNodeEntity]
    ) -> list[AnnotationNodeEntity]:
        with self.database.open_session() as session:
            session.add_all(nodes)
            # The nodes keep what they were given (and the ids flushing assigns)
            # instead of each being read again after the commit
            session.expire_on_commit = False
            session.commit()
        return nodes

    def update_node(self, node: AnnotationNodeEntity):
        with self.database.open_session() as session:
            session.merge(node)
            session.commit()

    def delete_node(self, node_id: int):
        with self.database.open_session() as session:
            stmt = delete(AnnotationNodeEntity).where(
                AnnotationNodeEntity.id == node_id
            )
            session.execute(stmt)
            session.commit()

    def delete_nodes_if_no_labels(self, node_ids: list[int]) -> list[int]:
        with self.database.open_session() as session:
            stmt = (
                delete(AnnotationNodeEntity)
                .where(
                    AnnotationNodeEntity.id.in_(node_ids),
                    ~exists().where(
                        or_(
                            AnnotationLabelEntity.start_node_id
                            == AnnotationNodeEntity.id,
                            AnnotationLabelEntity.end_node_id
                            == AnnotationNodeEntity.id,
                        )
                    ),
                )
                .returning(AnnotationNodeEntity.id)
            )
            result = session.execute(stmt)
            deleted_ids = [row.id for row in result.fetchall()]
            session.commit()

        return deleted_ids

    def add_types(self, types: list[AnnotationTypeEntity]):
        with self.database.open_session() as session:
            session.add_all(types)
            session.commit()

    def set_tier_talkers(self, annotation_id: int, talkers: dict[str, str]):
        """Says who produced each tier of an annotation (tier name -> talker name),
        adding the talker column to the table of tiers the first time any is known
        and the talker to the table of talkers if it is not there"""
        with self.database.engine.begin() as connection:
            present = {
                row[1]
                for row in connection.exec_driver_sql(
                    'PRAGMA table_info("annotation_type")'
                )
            }
            if "talker_id" not in present:
                connection.exec_driver_sql(
                    'ALTER TABLE "annotation_type" ADD COLUMN "talker_id" '
                    'INTEGER REFERENCES "talker" ("id")'
                )
            for tier, talker in talkers.items():
                connection.execute(
                    text(
                        'INSERT INTO "talker" ("name") SELECT :talker WHERE NOT EXISTS '
                        '(SELECT 1 FROM "talker" WHERE "name" = :talker)'
                    ),
                    {"talker": talker},
                )
                connection.execute(
                    text(
                        'UPDATE "annotation_type" SET "talker_id" = '
                        '(SELECT "id" FROM "talker" WHERE "name" = :talker) '
                        'WHERE "annotation_id" = :annotation AND "name" = :tier'
                    ),
                    {"talker": talker, "annotation": annotation_id, "tier": tier},
                )

    def read_tier_talkers(self, annotation_id: int) -> dict[int, str]:
        """The talker of each tier of an annotation that has one (tier id -> talker
        name); empty for a project in which no tier has a talker"""
        with self.database.engine.connect() as connection:
            if "talker_id" not in {
                row[1]
                for row in connection.exec_driver_sql(
                    'PRAGMA table_info("annotation_type")'
                )
            }:
                return {}
            rows = connection.execute(
                text(
                    'SELECT t."id", k."name" FROM "annotation_type" t '
                    'JOIN "talker" k ON k."id" = t."talker_id" '
                    'WHERE t."annotation_id" = :annotation'
                ),
                {"annotation": annotation_id},
            )
            return {row[0]: row[1] for row in rows}

    def add_label(self, label: AnnotationLabelEntity) -> AnnotationLabelEntity:
        with self.database.open_session() as session:
            session.add(label)
            session.commit()
            session.refresh(label)
        return label

    def merge_label(self, label: AnnotationLabelEntity):
        with self.database.open_session() as session:
            session.merge(label)
            session.commit()

    def delete_label(self, label: AnnotationLabelEntity):
        with self.database.open_session() as session:
            label = session.merge(label)
            session.delete(label)
            session.commit()

    def list_recordings(self) -> list[AnnotationEntity]:
        with self.database.open_session() as session:
            stmt = (
                select(AnnotationEntity)
                .order_by(AnnotationEntity.file_stem)
                .options(
                    selectinload(AnnotationEntity.talker_links).selectinload(
                        RecordingTalkerEntity.talker
                    ),
                )
            )
            return list(session.scalars(stmt))

    def list_channels(self) -> dict[int, list[RecordingChannelEntity]]:
        """The channel rows of each recording that has some (by recording id). A
        project without recordings stored as one file per channel has no such table"""
        if not self._has_channel_table():
            return {}
        with self.database.open_session() as session:
            rows = session.scalars(
                select(RecordingChannelEntity)
                .order_by(RecordingChannelEntity.id)
                .options(selectinload(RecordingChannelEntity.talker))
            )
            by_recording: dict[int, list[RecordingChannelEntity]] = {}
            for row in rows:
                by_recording.setdefault(row.recording_id, []).append(row)
            return by_recording

    def _has_channel_table(self) -> bool:
        return inspect(self.database.engine).has_table(
            RecordingChannelEntity.__tablename__
        )

    def upsert_recordings(
        self, recordings: list[Recording], remove_others: bool = True
    ) -> RecordingUpsertResult:
        """Creates or updates the annotation row of every recording in one
        transaction. With remove_others, rows of other recordings that hold no
        annotation content (no nodes and no tiers) are removed"""
        created = updated = removed = 0
        if any(recording.channel_files for recording in recordings):
            BaseEntity.metadata.tables[RecordingChannelEntity.__tablename__].create(
                self.database.engine, checkfirst=True
            )
        channels = self.list_channels()
        with self.database.open_session() as session:
            existing = {
                entity.file_stem: entity
                for entity in session.scalars(
                    select(AnnotationEntity).options(
                        selectinload(AnnotationEntity.talker_links).selectinload(
                            RecordingTalkerEntity.talker
                        )
                    )
                )
            }
            wanted = {recording.file_stem for recording in recordings}

            talkers = {
                talker.name: talker for talker in session.scalars(select(TalkerEntity))
            }
            for name in sorted(
                {
                    name
                    for r in recordings
                    for name in [*r.talkers, *r.channel_talkers.values()]
                }
                - talkers.keys()
            ):
                talkers[name] = TalkerEntity(name=name)
                session.add(talkers[name])

            for recording in recordings:
                entity = existing.get(recording.file_stem)
                if entity is None:
                    entity = AnnotationEntity(file_stem=recording.file_stem)
                    session.add(entity)
                    created += 1
                else:
                    updated += 1
                set_recording_columns(entity, recording)

                self._set_links(session, entity, recording, talkers)
                self._set_channels(session, entity, recording, talkers, channels)

            for file_stem, entity in existing.items():
                if not remove_others or file_stem in wanted:
                    continue
                has_content = session.scalar(
                    select(
                        exists().where(AnnotationTypeEntity.annotation_id == entity.id)
                        | exists().where(
                            AnnotationNodeEntity.annotation_id == entity.id
                        )
                    )
                )
                if not has_content:
                    if entity.id in channels:
                        session.execute(
                            delete(RecordingChannelEntity).where(
                                RecordingChannelEntity.recording_id == entity.id
                            )
                        )
                    session.delete(entity)
                    removed += 1

            session.commit()
        self._set_optional_columns(recordings)
        return RecordingUpsertResult(created, updated, removed)

    def _set_optional_columns(self, recordings: list[Recording]):
        """Set the video, media offset and target talker of the recordings, adding a
        column to the table first if some recording has a value for it and the table
        lacks it"""
        with self.database.engine.begin() as connection:
            present = {
                row[1]
                for row in connection.exec_driver_sql('PRAGMA table_info("recording")')
            }
            columns = [
                name
                for name in RECORDING_OPTIONAL_COLUMNS
                if name in present
                or any(getattr(r, name) is not None for r in recordings)
            ]
            for name in columns:
                if name not in present:
                    connection.exec_driver_sql(
                        f'ALTER TABLE "recording" ADD COLUMN "{name}" '
                        f"{RECORDING_OPTIONAL_COLUMNS[name]}"
                    )
            if columns:
                assignments = ", ".join(f'"{name}" = :{name}' for name in columns)
                connection.execute(
                    text(
                        f'UPDATE "recording" SET {assignments} '
                        "WHERE file_stem = :file_stem"
                    ),
                    [
                        {
                            "file_stem": recording.file_stem,
                            **{name: getattr(recording, name) for name in columns},
                        }
                        for recording in recordings
                    ],
                )

    def read_recording_optional_columns(self) -> dict[str, dict[str, Any]]:
        """The video, media offset and target talker of each recording that the table
        has columns for, by file stem; empty for a project that never had a value for
        any of them"""
        with self.database.engine.connect() as connection:
            present = {
                row[1]
                for row in connection.exec_driver_sql('PRAGMA table_info("recording")')
            }
            columns = [name for name in RECORDING_OPTIONAL_COLUMNS if name in present]
            if not columns:
                return {}
            selected = ", ".join(f'"{name}"' for name in columns)
            rows = connection.exec_driver_sql(
                f'SELECT file_stem, {selected} FROM "recording"'
            )
            return {row[0]: dict(zip(columns, row[1:])) for row in rows}

    def _set_links(
        self,
        session: Session,
        entity: AnnotationEntity,
        recording: Recording,
        talkers: dict[str, TalkerEntity],
    ):
        """Make the talkers linked to a recording the ones it has. Links that are
        already right are left alone; otherwise the old ones are deleted before the
        new ones are added, as a link may come back unchanged"""
        names = list(dict.fromkeys(recording.talkers))

        if [link.talker.name for link in entity.talker_links] != names:
            if entity.talker_links:
                entity.talker_links.clear()
                session.flush()
            entity.talker_links = [
                RecordingTalkerEntity(talker=talkers[name]) for name in names
            ]

    def _set_channels(
        self,
        session: Session,
        entity: AnnotationEntity,
        recording: Recording,
        talkers: dict[str, TalkerEntity],
        existing: dict[int, list[RecordingChannelEntity]],
    ):
        """Make the channel rows of a recording the ones it has (`existing` is what
        the database had when the update began). Rows that are already right are left
        alone."""
        wanted = [
            (channel, audio_file, recording.channel_talkers.get(channel))
            for channel, audio_file in recording.channel_files.items()
        ]
        current = [
            (row.channel, row.audio_file, row.talker.name if row.talker else None)
            for row in existing.get(entity.id, [])
        ]
        if wanted == current:
            return

        if entity.id is None:
            session.flush()  # a recording that is new has no id yet
        session.execute(
            delete(RecordingChannelEntity).where(
                RecordingChannelEntity.recording_id == entity.id
            )
        )
        session.add_all(
            RecordingChannelEntity(
                recording_id=entity.id,
                channel=channel,
                audio_file=audio_file,
                talker=talkers[talker] if talker is not None else None,
            )
            for channel, audio_file, talker in wanted
        )

    def list_talkers(self) -> list[str]:
        with self.database.open_session() as session:
            return list(
                session.scalars(select(TalkerEntity.name).order_by(TalkerEntity.name))
            )

    def builtin_columns(self, target: MetadataTarget) -> list[str]:
        entity, _, _ = METADATA_TABLES[target]
        names = [column.name for column in entity.__table__.columns]
        if target is MetadataTarget.RECORDING:
            names += list(RECORDING_OPTIONAL_COLUMNS)
        return names

    def add_metadata(
        self,
        target: MetadataTarget,
        columns: list[MetadataColumn],
        values: dict[str, dict[str, Any]],
    ) -> int:
        """Adds the columns to the table of `target` if it lacks them (SQLite adds a
        column to a table that has rows in it without rewriting it), then sets
        their values on the rows named in `values` (key -> column -> value).
        Returns how many rows were updated."""
        _, table, key_column = METADATA_TABLES[target]
        for column in columns:
            if not SAFE_NAME.fullmatch(column.name):
                raise ValueError(f"Not a usable column name: {column.name!r}")

        updated = 0
        with self.database.engine.begin() as connection:
            present = {
                row[1]
                for row in connection.exec_driver_sql(f'PRAGMA table_info("{table}")')
            }
            for column in columns:
                if column.name not in present:
                    connection.exec_driver_sql(
                        f'ALTER TABLE "{table}" ADD COLUMN "{column.name}" '
                        f"{column.sql_type.value}"
                    )

            if columns:
                assignments = ", ".join(
                    f'"{column.name}" = :v{index}'
                    for index, column in enumerate(columns)
                )
                statement = text(
                    f'UPDATE "{table}" SET {assignments} WHERE "{key_column}" = :key'
                )
                for key, row in values.items():
                    params: dict[str, Any] = {"key": key}
                    for index, column in enumerate(columns):
                        params[f"v{index}"] = row.get(column.name)
                    updated += connection.execute(statement, params).rowcount
        return updated

    def read_metadata(self, target: MetadataTarget) -> dict[str, dict[str, Any]]:
        """The columns users added to the table of `target`, for each row"""
        _, table, key_column = METADATA_TABLES[target]
        builtin = set(self.builtin_columns(target))
        with self.database.engine.connect() as connection:
            extra = [
                row[1]
                for row in connection.exec_driver_sql(f'PRAGMA table_info("{table}")')
                if row[1] not in builtin
            ]
            if not extra:
                return {}
            selected = ", ".join(f'"{name}"' for name in extra)
            rows = connection.exec_driver_sql(
                f'SELECT "{key_column}", {selected} FROM "{table}"'
            )
            return {row[0]: dict(zip(extra, row[1:])) for row in rows}

    def tier_label_counts(self, tier_name: str) -> dict[str, int]:
        with self.database.open_session() as session:
            stmt = (
                select(AnnotationLabelEntity.label_text, func.count())
                .join(
                    AnnotationTypeEntity,
                    AnnotationLabelEntity.annotation_type_id == AnnotationTypeEntity.id,
                )
                .where(AnnotationTypeEntity.name == tier_name)
                .group_by(AnnotationLabelEntity.label_text)
            )
            return {text: count for text, count in session.execute(stmt)}

    def replace_words(
        self, columns: list[MetadataColumn], rows: list[tuple[str, dict[str, Any]]]
    ) -> int:
        """Makes the word table again, with `columns` added to the word column, and a
        row for each of `rows` (word -> column -> value)"""
        for column in columns:
            if not SAFE_NAME.fullmatch(column.name):
                raise ValueError(f"Not a usable column name: {column.name!r}")

        table = BaseEntity.metadata.tables[WordEntity.__tablename__]
        with self.database.engine.begin() as connection:
            table.drop(connection, checkfirst=True)
            table.create(connection)
            for column in columns:
                connection.exec_driver_sql(
                    f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" '
                    f"{column.sql_type.value}"
                )
            names = ["word", *(column.name for column in columns)]
            statement = text(
                f'INSERT INTO "{table.name}" ({", ".join(f'"{n}"' for n in names)}) '
                f"VALUES ({', '.join(f':v{i}' for i in range(len(names)))})"
            )
            connection.execute(
                statement,
                [
                    {
                        "v0": word,
                        **{f"v{i}": row.get(c.name) for i, c in enumerate(columns, 1)},
                    }
                    for word, row in rows
                ],
            )
        return len(rows)

    def list_tables(self) -> list[str]:
        with self.database.engine.connect() as connection:
            names = [
                row[0]
                for row in connection.exec_driver_sql(
                    "SELECT name FROM sqlite_master WHERE type = 'table' "
                    "AND name NOT LIKE 'sqlite_%'"
                )
            ]
        first = [name for name in FIRST_TABLES if name in names]
        return first + sorted(name for name in names if name not in first)

    def read_table(self, name: str, limit: int) -> TableData:
        """The first rows of a table, for looking at. A column that points at a row of
        another table shows something readable from that row: the name of a talker or
        of a tier, the file stem of a recording, the time of a node"""
        if name not in self.list_tables():
            raise ValueError(f"The database has no table called {name!r}")
        with self.database.engine.connect() as connection:
            info = list(connection.exec_driver_sql(f'PRAGMA table_info("{name}")'))
            points_at = {
                row[3]: (row[2], row[4])  # column -> (table, its column there)
                for row in connection.exec_driver_sql(
                    f'PRAGMA foreign_key_list("{name}")'
                )
            }
            per_table = Counter(ref for ref, _ in points_at.values())

            selected, headers, joins = [], [], []
            for index, row in enumerate(info):
                column = row[1]
                reference = points_at.get(column)
                if reference is not None and reference[0] in READABLE_COLUMN:
                    table, to = reference
                    alias = f"pointed{index}"
                    joins.append(
                        f'LEFT JOIN "{table}" AS {alias} '
                        f'ON {alias}."{to}" = t."{column}"'
                    )
                    value = f'{alias}."{READABLE_COLUMN[table]}"'
                    selected.append(
                        _three_places(value) if table == NODE_TABLE else value
                    )
                    headers.append(
                        table if per_table[table] == 1 else column.removesuffix("_id")
                    )
                else:
                    value = f't."{column}"'
                    is_time = name == NODE_TABLE and column == "time"
                    selected.append(_three_places(value) if is_time else value)
                    headers.append(column)

            total = connection.exec_driver_sql(
                f'SELECT COUNT(*) FROM "{name}"'
            ).scalar()
            rows = connection.exec_driver_sql(
                f'SELECT {", ".join(selected)} FROM "{name}" AS t '
                f"{' '.join(joins)} LIMIT {int(limit)}"
            )
            return TableData(
                name, headers, [list(row) for row in rows], int(total or 0)
            )
