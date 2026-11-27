from dataclasses import dataclass, field
from typing import Literal

from core.annotation.entity.recording import Recording
from core.project.entity.project_file import ProjectFile
from core.project_layout.entity.import_report import ImportReport, LayoutSuggestion
from core.project_layout.entity.project_layout import ProjectLayout

LayoutSource = Literal["given", "saved", "inferred"]

MAX_EXAMPLES = 3


@dataclass(frozen=True)
class ProjectPlan:
    """What reading a project folder with a layout finds, before anything is written:
    its recordings, how the layout was arrived at, and what did not fit it.

    `layout_source` says whether the layout was given, saved in the project's
    phonlab.toml, or inferred from the files (the last is a guess; `suggestion` holds
    the evidence for it)."""

    root: str
    layout: ProjectLayout
    layout_source: LayoutSource
    files: list[ProjectFile] = field(default_factory=list)
    report: ImportReport = field(default_factory=ImportReport)
    suggestion: LayoutSuggestion | None = None
    # the layout's filename template could not be used, so no variables were taken from
    # file names
    template_unusable: bool = False

    @property
    def recordings(self) -> list[Recording]:
        return [f.recording for f in self.files if f.recording is not None]

    @property
    def problems(self) -> list[str]:
        """What a person should look at before the project is imported: the project
        has things the layout does not account for, or the layout was guessed and the
        guess is not clear. Empty when the project reads cleanly."""
        report, found = self.report, []
        if not self.files:
            found.append("no sound files were found")
        if self.template_unusable:
            found.append("the filename template cannot be used")
        found += _examples(
            report.template_mismatches, "sound files do not fit the filename template"
        )
        found += _examples(
            report.duplicate_audio, "sound files look like copies of others"
        )
        found += _examples(
            report.unpaired_annotations, "annotation files belong to no sound file"
        )
        found += self._guess_problems()
        return found

    def _guess_problems(self) -> list[str]:
        suggestion = self.suggestion
        if suggestion is None:
            return []
        found = []
        sources = suggestion.annotation_sources.get(self.layout.annotation_ext or "")
        if sources is not None and sources.overlapping:
            found.append(
                f"{self.layout.annotation_ext} files are kept in several folders that "
                "hold the same recordings: say which to read (annotation_dir)"
            )
        candidate = suggestion.channel_candidate
        if candidate is not None and candidate.looks_like_channels is None:
            found.append(
                f"{candidate.n_groups} groups of sound files are named like the "
                "channels of one recording but could not be read to check: say "
                "whether they are (channels)"
            )
        return found

    def __str__(self) -> str:
        layout, report = self.layout, self.report
        lines = [
            f"Project {self.root}",
            f"Layout: {self.layout_source}",
            (
                f"{report.n_recordings} recordings, {report.n_annotated} with an "
                f"annotation ({layout.annotation_ext or 'none'})"
            ),
        ]
        if layout.levels:
            named = [
                f"{level.depth}: {level.field or '(not used)'}"
                for level in layout.levels
            ]
            lines.append("Folder levels: " + ", ".join(named))
        if layout.filename_template:
            lines.append(f"Filename template: {layout.filename_template}")
        if layout.channels:
            lines.append("Channels: " + ", ".join(c.label for c in layout.channels))
        if report.data_file_counts:
            lines.append(
                "Other files: "
                + ", ".join(f"{k} ({n})" for k, n in report.data_file_counts.items())
            )
        for recording in self.recordings[:MAX_EXAMPLES]:
            talkers = ", ".join(recording.talkers) or "-"
            lines.append(f"  {recording.file_stem}  talkers: {talkers}")
        lines += [f"Needs a look: {problem}" for problem in self.problems]
        return "\n".join(lines)


def _examples(paths: list[str], what: str) -> list[str]:
    if not paths:
        return []
    shown = ", ".join(paths[:MAX_EXAMPLES])
    return [f"{len(paths)} {what} (for example {shown})"]
