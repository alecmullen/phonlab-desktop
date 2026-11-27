from dataclasses import replace
from pathlib import Path

from phonlab_project.constants import CHAT_TARGET_CODE
from phonlab_project.readers.read_chat import read_chat_speakers
from phonlab_project.recording import Recording


def name_chat_speakers(recordings: list[Recording], root: str) -> list[Recording]:
    """Says who made each tier of the recordings whose annotation is a CHAT (.cha) file.

    A CHAT file names its speakers by role, not by name. The speaker `PAR` is the talker
    the folder and file names give the recording, if they give one. Every other speaker
    is taken to be a different person in each file: the interviewer of one recording is
    not assumed to be the interviewer of the next. They are named by their code and a
    number that counts up through the recordings, in order (`INV1`, `INV2`, `UID1`...).
    The numbers depend on the files the project has, so adding a recording that sorts
    before others renumbers those after it.

    The talkers of each recording are those the layout gave it and those of its tiers."""
    counts: dict[str, int] = {}
    named: list[Recording] = []
    for recording in recordings:
        annotation = recording.annotation_file
        if annotation is None or not annotation.casefold().endswith(".cha"):
            named.append(recording)
            continue
        try:
            codes = read_chat_speakers(str(Path(root) / annotation))
        except OSError:
            named.append(recording)
            continue

        target = recording.talkers[0] if len(recording.talkers) == 1 else None
        tier_talkers: dict[str, str] = {}
        for code in codes:
            if code == CHAT_TARGET_CODE and target is not None:
                tier_talkers[code] = target
                continue
            counts[code] = counts.get(code, 0) + 1
            joint = "_" if code[-1:].isdigit() else ""
            tier_talkers[code] = f"{code}{joint}{counts[code]}"
        talkers = list(dict.fromkeys([*recording.talkers, *tier_talkers.values()]))
        named.append(replace(recording, tier_talkers=tier_talkers, talkers=talkers))
    return named
