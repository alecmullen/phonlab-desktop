import time

from sqlalchemy import Row, delete, exists, or_, select
from sqlalchemy.orm import aliased, selectinload

from data.annotation.entity.annotation import AnnotationEntity
from data.annotation.entity.annotation_label import AnnotationLabelEntity
from data.annotation.entity.annotation_node import AnnotationNodeEntity
from data.annotation.entity.annotation_type import AnnotationTypeEntity
from data.base.datasource import DataSource


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
            start_time = time.perf_counter()
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
            print("GET ANNOT:", time.perf_counter() - start_time)

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
            session.commit()
            for node in nodes:
                session.refresh(node)
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
