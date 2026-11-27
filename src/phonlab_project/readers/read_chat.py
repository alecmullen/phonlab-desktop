import re
from pathlib import Path
from typing import Any

# A time bullet, which CHAT writes between NAK (0x15) characters: start and end in
# milliseconds
BULLET = re.compile("\x15(\\d+)_(\\d+)\x15")
UTTERANCE = re.compile(r"\*([^:\s]+):\t?(.*)", re.DOTALL)


def read_chat_tiers(file_path: str) -> list[dict[str, Any]]:
    """Reads a CHAT (.cha) transcript, as TalkBank corpora keep them, into one tier per
    speaker whose labels are that speaker's utterances from the time each begins to the
    time it ends. The tiers are named by the speaker's code (`PAR`, `INV`) and are in
    the order the speakers first speak. A CHAT file names no talkers, only roles, so
    the tiers have no `talker`.

    Only the main lines (`*PAR:`) are read, with their time bullets taken out and their
    CHAT codes (`&-um`, `[//]`) left in. An utterance with no time bullet is left out,
    since it has no place on the timeline. Aligners pad utterances, so one speaker's
    utterances can overlap a little; where they do, the boundary between them is moved
    to the middle of the overlap. An utterance inside another by the same speaker (a
    quotation marker said within a longer turn) is kept as it is, so a tier can still
    have a few overlapping labels."""
    try:
        text = Path(file_path).read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(f"Cannot read {file_path} as a CHAT file: {error}") from error
    lines = text.splitlines()
    if not any(line.startswith("@Begin") for line in lines):
        raise ValueError(f"Cannot read {file_path} as a CHAT file: no @Begin line")

    tiers: dict[str, list[list[Any]]] = {}
    for speaker, utterance in _utterances(lines):
        bullets = BULLET.findall(utterance)
        words = " ".join(BULLET.sub(" ", utterance).split())
        labels = tiers.setdefault(speaker, [])
        if not bullets or not words:
            continue
        start, end = (int(ms) for ms in bullets[-1])
        if end < start:
            continue
        _add(labels, start, end, words)

    return [
        {"name": name, "labels": [(b / 1000, e / 1000, w) for b, e, w in labels]}
        for name, labels in tiers.items()
    ]


def read_chat_speakers(file_path: str) -> list[str]:
    """The codes of the speakers of a CHAT file (`INV`, `PAR`) in the order they first
    speak: the names of the tiers `read_chat_tiers` makes"""
    text = Path(file_path).read_text(encoding="utf-8-sig", errors="replace")
    codes: dict[str, None] = {}
    for line in text.splitlines():
        found = UTTERANCE.fullmatch(line) if line.startswith("*") else None
        if found:
            codes.setdefault(found.group(1))
    return list(codes)


def _utterances(lines: list[str]):
    """(speaker, text) of each main line; a line that starts with a tab continues the
    one before it"""
    speaker: str | None = None
    parts: list[str] = []
    for line in lines:
        if line.startswith("\t") and speaker is not None:
            parts.append(line)
            continue
        if speaker is not None:
            yield speaker, " ".join(parts)
            speaker = None
        found = UTTERANCE.fullmatch(line) if line.startswith("*") else None
        if found:
            speaker, parts = found.group(1), [found.group(2)]
    if speaker is not None:
        yield speaker, " ".join(parts)


def _add(labels: list[list[Any]], start: int, end: int, words: str) -> None:
    """Adds an utterance (times in milliseconds), moving the boundary with the one
    before it to the middle of where they overlap"""
    if labels:
        before = labels[-1]
        if before[0] <= start < before[1] < end:
            middle = (start + before[1]) / 2
            before[1] = start = middle
    labels.append([start, end, words])
