from dataclasses import dataclass, field
from typing import Literal

from phonlab_project.layout.import_report import ImportReport, LayoutSuggestion
from phonlab_project.layout.project_file import ProjectFile
from phonlab_project.layout.project_layout import ProjectLayout
from phonlab_project.recording import Recording

LayoutSource = Literal["given", "saved", "inferred"]

MAX_EXAMPLES = 3


@dataclass(frozen=True)
class ProjectPlan:
    """What reading a project folder with a layout finds, before anything is written.

    Made by `describe_project`; `print(plan)` describes it.

    Attributes
    ----------

    root : str
        The project folder.

    layout : ProjectLayout
        The layout used.

    layout_source : {"given", "saved", "inferred"}
        Where the layout came from: the one given, the one saved in the folder's
        `phonlab.toml`, or one guessed from the files.

    files : list
        The recordings with the paths of their files.

    report : ImportReport
        Counts of recordings and annotated recordings, and the lists of unpaired sound
        files and annotation files, copies, and names that do not fit the template.

    suggestion : LayoutSuggestion or None
        The evidence for an inferred layout.

    template_unusable : bool
        The layout's filename template could not be used, so no variables were taken
        from file names.

    recordings : list of Recording
        The recordings (property).

    problems : list of str
        What a person should look at before the project is imported (property): things
        the layout does not account for, or a guessed layout whose guess is not clear.
        Empty when the project reads cleanly."""

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
