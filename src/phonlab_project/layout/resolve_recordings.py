from phonlab_project.layout.channels import group_audio
from phonlab_project.layout.duplicate_audio import find_duplicate_audio
from phonlab_project.layout.filename_template import compile_template
from phonlab_project.layout.import_report import ImportReport, ResolvedProject
from phonlab_project.layout.pairing import AudioIndex, reroot
from phonlab_project.layout.project_layout import DataFileKind, ProjectLayout
from phonlab_project.layout.project_scan import ProjectScan, ScannedFile
from phonlab_project.recording import Recording
from res.constants import TALKER_FIELD_NAMES


def resolve_recordings(scan: ProjectScan, layout: ProjectLayout) -> ResolvedProject:
    """Applies a layout to a scanned project: pairs each audio file with its
    annotation and data files, takes the talkers and other variables from the
    folder and file names, and reports what did not fit. Nothing is written.

    Raises `TemplateError` if the layout's filename template is invalid."""
    template = (
        compile_template(layout.filename_template)
        if layout.filename_template.strip() != ""
        else None
    )

    audio_files = [f for f in scan.files if f.ext in layout.audio_ext]
    units = group_audio(audio_files, layout.channels)
    audio = [unit.base for unit in units]
    unit_for = {unit.base.path: unit for unit in units}
    index = AudioIndex(audio)

    annotation_for: dict[str, ScannedFile] = {}
    unpaired_annotations: list[str] = []
    if layout.annotation_ext is not None:
        for file in scan.files:
            if file.ext != layout.annotation_ext or not (
                layout.reads_annotations_from(file.dir)
            ):
                continue
            found = index.owner(file, allow_suffix=False)
            if found is None and layout.annotation_dir:
                found = index.owner(
                    reroot(file, layout.annotation_dir), allow_suffix=False
                )
            if found is None or found[0].path in annotation_for:
                unpaired_annotations.append(file.path)
            else:
                annotation_for[found[0].path] = file

    role_names = {role.key: role.name for role in layout.data_files}
    role_exts = {ext for _, ext in role_names}
    data_for: dict[str, dict[str, str]] = {}
    for file in scan.files:
        if file.ext not in role_exts or file.ext in layout.audio_ext:
            continue
        found = index.owner(file, allow_suffix=True)
        if found is None:
            continue
        owner, suffix = found
        name = role_names.get((suffix.casefold(), file.ext))
        if name is not None:
            data_for.setdefault(owner.path, {}).setdefault(name, file.path)

    roles = {role.name: role for role in layout.data_files}

    recordings: list[Recording] = []
    unpaired_audio: list[str] = []
    mismatches: list[str] = []
    seen_stems: set[str] = set()
    counts = {role.name: 0 for role in layout.data_files}

    for file in audio:
        unit = unit_for[file.path]
        annotation = annotation_for.get(file.path)
        data_files: dict[str, str] = {}
        tier_files: dict[str, str] = {}
        for name, path in data_for.get(file.path, {}).items():
            if roles[name].kind is DataFileKind.ANNOTATION:
                tier_files[roles[name].tier_name] = path
            else:
                data_files[name] = path

        if annotation is None and not tier_files:
            unpaired_audio.append(unit.first_file.path)
            if not layout.include_unpaired_audio:
                continue

        file_stem = file.path_without_ext
        if file_stem in seen_stems:
            continue
        seen_stems.add(file_stem)

        talkers: list[str] = []
        fields: dict[str, str] = {}

        parts = file.dir.split("/") if file.dir else []
        for level in layout.levels:
            if level.field and level.depth <= len(parts):
                _add_variable(talkers, fields, level.field, parts[level.depth - 1])

        if template is not None:
            pairs = template.match(file.stem)
            if pairs is None:
                mismatches.append(file.path)
            else:
                for name, value in pairs:
                    _add_variable(talkers, fields, name, value)

        channel_files = {label: f.path for label, f in unit.channels.items()}
        channel_talkers = {
            role.label: role.talker
            for role in layout.channels
            if role.talker and role.label in channel_files
        }
        for talker in channel_talkers.values():
            _add_variable(talkers, fields, "talker", talker)

        for name in data_for.get(file.path, {}):
            counts[name] += 1

        recordings.append(
            Recording(
                file_stem=file_stem,
                audio_file=unit.first_file.path,
                channel_files=channel_files,
                channel_talkers=channel_talkers,
                annotation_file=annotation.path if annotation else None,
                tier_files=tier_files,
                data_files=data_files,
                talkers=talkers,
                fields=fields,
            )
        )

    report = ImportReport(
        n_audio=len(audio),
        n_audio_files=len(audio_files),
        n_recordings=len(recordings),
        n_annotated=sum(1 for r in recordings if r.annotation_file or r.tier_files),
        unpaired_audio=unpaired_audio,
        unpaired_annotations=unpaired_annotations,
        duplicate_audio=find_duplicate_audio(audio_files, scan.root),
        template_mismatches=mismatches,
        data_file_counts=counts,
    )
    return ResolvedProject(recordings, report)


def _add_variable(
    talkers: list[str], fields: dict[str, str], name: str, value: str
) -> None:
    """Records a value taken from a folder or file name: talkers go in the list of
    talkers, anything else in the fields, where a second different value for the
    same variable is added after a |"""
    if name.casefold() in TALKER_FIELD_NAMES:
        if value not in talkers:
            talkers.append(value)
    elif name not in fields:
        fields[name] = value
    elif value not in fields[name].split("|"):
        fields[name] += f"|{value}"
