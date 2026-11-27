import os
from collections import Counter
from dataclasses import dataclass, field

import soundfile as sf

from phonlab_project.constants import CHANNEL_MIN_COVERAGE, CHANNEL_SAMPLE_GROUPS
from phonlab_project.layout.import_report import ChannelCandidate
from phonlab_project.layout.pairing import candidate_splits
from phonlab_project.layout.project_layout import ChannelRole
from phonlab_project.layout.project_scan import ScannedFile

MAX_EXAMPLES = 3
MAX_CHANNELS = 8
# the label of the channel whose file is named exactly like the recording
NO_ENDING_LABEL = "main"


@dataclass(frozen=True)
class AudioUnit:
    """What is imported as one recording: an audio file, or the audio files that
    are its channels. `base` is the file the rest of the recording (annotation,
    data files) is named after; for channel files it does not exist on disk."""

    base: ScannedFile
    channels: dict[str, ScannedFile] = field(default_factory=dict)

    @property
    def first_file(self) -> ScannedFile:
        return next(iter(self.channels.values()), self.base)


def group_audio(
    audio: list[ScannedFile], channels: tuple[ChannelRole, ...]
) -> list[AudioUnit]:
    """Groups channel files into recordings. A file is a channel when its name ends
    with a channel's suffix and the same folder holds the other channels under the
    same base name; anything else stays a recording of its own. A channel's suffix may
    be empty: its file is the one named exactly like the recording (rl001.wav next to
    rl001_lar.wav)."""
    if not channels:
        return [AudioUnit(file) for file in audio]

    by_suffix = sorted(channels, key=lambda role: len(role.suffix), reverse=True)
    groups: dict[tuple[str, str, str], dict[str, ScannedFile]] = {}
    bases: dict[tuple[str, str, str], str] = {}
    membership: dict[str, tuple[str, str, str]] = {}
    for file in audio:
        for role in by_suffix:
            suffix = role.suffix.casefold()
            if file.stem.casefold().endswith(suffix) and len(file.stem) > len(suffix):
                base = file.stem[: len(file.stem) - len(suffix)]
                key = (file.dir, base.casefold(), file.ext)
                groups.setdefault(key, {})[role.label] = file
                bases.setdefault(key, base)
                membership[file.path] = key
                break

    units: list[AudioUnit] = []
    emitted: set[tuple[str, str, str]] = set()
    for file in audio:
        key = membership.get(file.path)
        if key is None or len(groups[key]) < 2:
            units.append(AudioUnit(file))
            continue
        if key in emitted:
            continue
        emitted.add(key)
        ordered = {
            role.label: groups[key][role.label]
            for role in channels
            if role.label in groups[key]
        }
        first = next(iter(ordered.values()))
        base_path = f"{first.dir}/" if first.dir else ""
        base_path += bases[key] + first.name[len(first.stem) :]
        units.append(AudioUnit(ScannedFile.from_path(base_path), ordered))
    return units


def detect_channels(audio: list[ScannedFile], root: str) -> ChannelCandidate | None:
    """Looks for audio files that differ only by a repeating suffix such as _L and
    _R. Whether they are channels or, say, takes is judged from the file headers: files
    that are not mono and equally long are not offered, and suffixes that are only
    numbers (item_01, item_02) are offered only when the headers show channels."""
    groups: dict[tuple[str, str, str], dict[str, tuple[ScannedFile, str]]] = {}
    for file in audio:
        # a file named exactly like the recording is the channel with no ending
        own_key = (file.dir, file.stem.casefold(), file.ext)
        groups.setdefault(own_key, {})[""] = (file, "")

        splits = candidate_splits(file.stem)
        if len(splits) < 2:
            continue
        base, suffix = splits[1]  # the shortest suffix: what follows the last delimiter
        key = (file.dir, base.casefold(), file.ext)
        groups.setdefault(key, {})[suffix.casefold()] = (file, suffix)

    paired = {key: group for key, group in groups.items() if len(group) >= 2}
    if not paired:
        return None
    signatures = Counter(tuple(sorted(group)) for group in paired.values())
    signature, n_groups = signatures.most_common(1)[0]
    members = [group for group in paired.values() if tuple(sorted(group)) == signature]
    n_files = sum(len(group) for group in members)
    if n_files / len(audio) < CHANNEL_MIN_COVERAGE:
        return None

    roles = tuple(
        ChannelRole(
            label=members[0][key][1].lstrip("_-.") or NO_ENDING_LABEL,
            suffix=members[0][key][1],
        )
        for key in signature
    )
    examples = [
        " + ".join(file.name for file, _ in group.values())
        for group in members[:MAX_EXAMPLES]
    ]
    looks_like = _looks_like_channels(root, members[:CHANNEL_SAMPLE_GROUPS])
    if looks_like is False or len(roles) > MAX_CHANNELS:
        return None  # takes or numbered items, not channels
    if all(role.label.isdigit() for role in roles) and looks_like is not True:
        return None  # numbers alone say nothing: only the headers can show channels
    return ChannelCandidate(roles, n_groups, examples, looks_like)


def _looks_like_channels(
    root: str, groups: list[dict[str, tuple[ScannedFile, str]]]
) -> bool | None:
    try:
        for group in groups:
            infos = [
                sf.info(os.path.join(root, file.path)) for file, _ in group.values()
            ]
            if any(info.channels != 1 for info in infos):
                return False
            if len({(info.frames, info.samplerate) for info in infos}) != 1:
                return False
    except (RuntimeError, OSError):
        return None
    return True
