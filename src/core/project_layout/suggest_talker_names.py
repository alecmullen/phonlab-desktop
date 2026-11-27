import os
from collections.abc import Iterable

from core.base.use_case_sync import UseCaseSync
from phonlab_project.constants import SRT_NO_TALKER_TIER
from phonlab_project.readers.read_tiers import read_tiers

SEPARATOR = " - "
# what tiers are usually called when the name is about content, not a talker
TIER_KINDS = (
    "word",
    "phone",
    "segment",
    "syllable",
    "transcript",
    "ort",
    "mau",
    "utterance",
    "sentence",
    "note",
    "comment",
    "tone",
    "log",
    SRT_NO_TALKER_TIER,
)


def talker_names_from_tiers(tier_names: list[str]) -> list[str]:
    """Names of the talkers an annotation's tiers suggest. Tiers named like
    "Anna - words" (or "words - Anna") give the part that is not about content;
    otherwise any tier whose whole name does not look like a kind of tier is taken
    to be named after a talker."""
    split = [name.split(SEPARATOR, 1) for name in tier_names if SEPARATOR in name]
    if len(split) == len([n for n in tier_names if SEPARATOR in n]) and split:
        left = [parts[0].strip() for parts in split]
        right = [parts[1].strip() for parts in split]
        if all(_is_kind(part) for part in right):
            return _unique(left)
        if all(_is_kind(part) for part in left):
            return _unique(right)
        return []
    return _unique(name.strip() for name in tier_names if not _is_kind(name))


def _is_kind(name: str) -> bool:
    folded = name.strip().casefold()
    return folded.startswith(TIER_KINDS)


def _unique(names: Iterable[str]) -> list[str]:
    seen: list[str] = []
    for name in names:
        if name and name not in seen:
            seen.append(name)
    return seen


class SuggestTalkerNames(UseCaseSync[list[str]]):
    """Reads the tier names of one annotation file for names of talkers, to offer
    when the user is asked who is on each channel"""

    def __call__(self, dir_path: str, annotation_file: str) -> list[str]:
        try:
            tiers = read_tiers(os.path.join(dir_path, annotation_file))
        except Exception:  # noqa: BLE001 - an unreadable file just gives no suggestions
            return []
        return talker_names_from_tiers([str(tier["name"]) for tier in tiers])
