from collections import Counter

from core.base.use_case_sync import UseCaseSync
from phonlab_project.layout.annotation_sources import find_annotation_sources
from phonlab_project.layout.channels import detect_channels, group_audio
from phonlab_project.layout.import_report import (
    DataFileCandidate,
    FolderSources,
    LayoutSuggestion,
    LevelSummary,
)
from phonlab_project.layout.pairing import AudioIndex
from phonlab_project.layout.project_layout import (
    ChannelRole,
    DataFileRole,
    FolderLevel,
    ProjectLayout,
)
from phonlab_project.layout.project_scan import ProjectScan, ScannedFile
from res.constants import (
    ANNOTATION_COMPANION_EXTENSIONS,
    ANNOTATION_FORMATS,
    DATA_FILE_MIN_COVERAGE,
    PROJECT_AUDIO_EXTENSIONS,
)

NAME_PREFIX_TALKER_SHARE = 0.9
MAX_EXAMPLES = 4


class InferLayout(UseCaseSync[LayoutSuggestion]):
    """Proposes a layout for a scanned project from the evidence in the file
    tree alone: which extensions pair up with the audio files, which kinds of
    extra files accompany the recordings, and what the folder levels look like. Everything it proposes can be changed by the user."""

    def __call__(
        self, scan: ProjectScan, channels: tuple[ChannelRole, ...] | None = None
    ) -> LayoutSuggestion:
        """`channels` is the user's decision about audio files that are channels of
        a recording; if it is None they are taken as channels only when the file
        headers show they are"""
        audio_files = [f for f in scan.files if f.ext in PROJECT_AUDIO_EXTENSIONS]
        channel_candidate = detect_channels(audio_files, scan.root)
        if channels is None:
            use_channels = channel_candidate is not None and (
                channel_candidate.looks_like_channels is True
            )
            channels = (
                channel_candidate.roles if use_channels and channel_candidate else ()
            )

        audio = [unit.base for unit in group_audio(audio_files, channels)]
        index = AudioIndex(audio)

        annotation_sources = {
            ext: find_annotation_sources([f for f in scan.files if f.ext == ext], index)
            for ext in ANNOTATION_FORMATS
        }
        annotation_ext = max(
            (
                ext
                for ext, sources in annotation_sources.items()
                if sources.n_paired > 0
            ),
            key=lambda ext: annotation_sources[ext].n_paired,
            default=None,
        )

        candidates = self._data_file_candidates(scan, audio, index, annotation_ext)
        levels, talker_depth = self._levels(audio)

        layout = ProjectLayout(
            annotation_ext=annotation_ext,
            annotation_dir=annotation_sources.get(
                annotation_ext or "", FolderSources()
            ).default,
            channels=channels,
            levels=tuple(
                FolderLevel(
                    summary.depth, "talker" if summary.depth == talker_depth else ""
                )
                for summary in levels
            ),
            data_files=tuple(
                c.role for c in candidates if c.coverage >= DATA_FILE_MIN_COVERAGE
            ),
        )
        return LayoutSuggestion(
            layout,
            levels,
            candidates,
            annotation_sources,
            channel_candidate,
        )

    def _data_file_candidates(
        self,
        scan: ProjectScan,
        audio: list[ScannedFile],
        index: AudioIndex,
        annotation_ext: str | None,
    ) -> list[DataFileCandidate]:
        skipped = {*PROJECT_AUDIO_EXTENSIONS, ""}
        if annotation_ext is not None:
            skipped.add(annotation_ext)
            skipped.update(
                ANNOTATION_COMPANION_EXTENSIONS.get(
                    ANNOTATION_FORMATS[annotation_ext], ()
                )
            )

        counts: Counter[tuple[str, str]] = Counter()
        suffixes: dict[tuple[str, str], str] = {}
        owners: dict[tuple[str, str], set[str]] = {}
        for file in scan.files:
            if file.ext in skipped:
                continue
            found = index.owner(file, allow_suffix=True)
            if found is None:
                continue
            owner, suffix = found
            key = (suffix.casefold(), file.ext)
            suffixes.setdefault(key, suffix)
            if owner.path not in owners.setdefault(key, set()):
                owners[key].add(owner.path)
                counts[key] += 1

        candidates: list[DataFileCandidate] = []
        used_names: set[str] = set()
        for key, count in counts.most_common():
            name = _role_name(suffixes[key], key[1])
            unique, number = name, 1
            while unique in used_names:
                number += 1
                unique = f"{name}_{number}"
            used_names.add(unique)
            role = DataFileRole(unique, suffixes[key], key[1])
            candidates.append(DataFileCandidate(role, count, count / len(audio)))
        return candidates

    def _levels(
        self, audio: list[ScannedFile]
    ) -> tuple[list[LevelSummary], int | None]:
        dirs = [f.dir.split("/") if f.dir else [] for f in audio]
        max_depth = max((len(parts) for parts in dirs), default=0)

        summaries: list[LevelSummary] = []
        for depth in range(1, max_depth + 1):
            at_depth = [
                (parts[depth - 1], file)
                for parts, file in zip(dirs, audio)
                if len(parts) >= depth
            ]
            values = sorted({value for value, _ in at_depth})
            with_prefix = sum(
                1
                for value, file in at_depth
                if file.stem.casefold().startswith(value.casefold())
            )
            summaries.append(
                LevelSummary(
                    depth,
                    len(values),
                    values[:MAX_EXAMPLES],
                    len(at_depth),
                    with_prefix / len(at_depth),
                )
            )

        # file names that begin with the folder name are strong evidence that the
        # folder names the talker; otherwise the deepest level that varies is the
        # best guess
        named = [
            s
            for s in summaries
            if s.n_values > 1 and s.name_prefix_share >= NAME_PREFIX_TALKER_SHARE
        ]
        varying = [s for s in summaries if s.n_values > 1]
        if named:
            talker_depth = named[-1].depth
        elif varying:
            talker_depth = varying[-1].depth
        else:
            talker_depth = None
        return summaries, talker_depth


def _role_name(suffix: str, ext: str) -> str:
    base = suffix.lstrip("_-.")
    extension = ext.lstrip(".")
    return f"{base}_{extension}" if base and extension else base or extension or "data"
