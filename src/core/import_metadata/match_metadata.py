from pathlib import PurePosixPath

from core.annotation.entity.metadata import MetadataTarget
from core.annotation.entity.recording import Recording
from core.annotation.repository.annotation_repository import AnnotationRepository
from core.base.use_case_sync import UseCaseSync
from core.import_metadata.entity.metadata_table import MetadataMatch, MetadataTable

MAX_UNMATCHED_EXAMPLES = 8


class MatchMetadata(UseCaseSync[MetadataMatch]):
    """Works out which talker or recording each row of a table is about, from one
    column that holds a name. Case and surrounding spaces do not matter.

    A talker is named by its name. A recording may be named by its path without
    the extension (folder/take1), by its audio file's path or name (take1.wav), or
    by the bare name without extension (take1) if no other recording has it; the way
    that matches the most rows is used."""

    def __init__(self, annotation_repository: AnnotationRepository):
        self.annotation_repository = annotation_repository

    def __call__(
        self, table: MetadataTable, target: MetadataTarget, key_column: str
    ) -> MetadataMatch:
        values = [value.strip() for value in table.column(key_column)]
        if target == MetadataTarget.TALKER:
            names = self.annotation_repository.list_talkers()
            lookups = {"name": {name.casefold(): name for name in names}}
            target_keys = names
        else:
            recordings = self.annotation_repository.list_recordings()
            lookups = _recording_lookups(recordings)
            target_keys = [recording.file_stem for recording in recordings]

        best_strategy, best = "", {}
        for strategy, lookup in lookups.items():
            found = {
                index: lookup[value.casefold()]
                for index, value in enumerate(values)
                if value.casefold() in lookup
            }
            if len(found) > len(best) or best_strategy == "":
                best_strategy, best = strategy, found

        matches: dict[int, str] = {}
        seen: set[str] = set()
        n_duplicates = 0
        for index, key in best.items():
            if key in seen:
                n_duplicates += 1
            seen.add(key)
            matches[index] = key

        unmatched_targets = sorted(set(target_keys) - seen)[:MAX_UNMATCHED_EXAMPLES]

        return MetadataMatch(
            target=target,
            key_column=key_column,
            strategy=best_strategy,
            n_rows=len(values),
            matches=matches,
            unmatched_values=[
                value
                for index, value in enumerate(values)
                if index not in matches and value
            ][:MAX_UNMATCHED_EXAMPLES],
            n_duplicates=n_duplicates,
            n_unmatched_targets=len(target_keys) - len(seen),
            n_targets=len(target_keys),
            unmatched_targets=unmatched_targets,
        )


def _recording_lookups(recordings: list[Recording]) -> dict[str, dict[str, str]]:
    by_stem: dict[str, str] = {}
    by_audio_path: dict[str, str] = {}
    base_names: dict[str, list[str]] = {}
    audio_names: dict[str, list[str]] = {}
    for recording in recordings:
        stem = recording.file_stem
        by_stem[stem.casefold()] = stem
        base_names.setdefault(PurePosixPath(stem).name.casefold(), []).append(stem)
        if recording.audio_file:
            by_audio_path[recording.audio_file.casefold()] = stem
            audio_names.setdefault(
                PurePosixPath(recording.audio_file).name.casefold(), []
            ).append(stem)

    def only_unique(names: dict[str, list[str]]) -> dict[str, str]:
        return {name: stems[0] for name, stems in names.items() if len(stems) == 1}

    return {
        "file path": by_stem,
        "audio file path": by_audio_path,
        "file name": only_unique(base_names),
        "audio file name": only_unique(audio_names),
    }
