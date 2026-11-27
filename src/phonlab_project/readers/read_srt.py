import re
from pathlib import Path
from typing import Any

import srt

from phonlab_project.constants import SRT_NO_TALKER_TIER, SRT_TALKER_MAX_LENGTH

# A talker's name at the start of a subtitle: "Camille: Okay, ..."
TALKER_PREFIX = re.compile(r"^([^:\s][^:]*?)\s*:(?:\s+|$)")


def read_srt_tiers(file_path: str) -> list[dict[str, Any]]:
    """Reads a subtitle (.srt) file into one tier per talker, whose labels are that
    talker's subtitles from the time each begins to the time it ends. A subtitle
    names its talker only when the talker changes ("Camille: Okay"), so one without
    a name belongs to the talker of the subtitle before it. Subtitles before any
    talker is named, or all of them when none is, go to a tier with no talker.
    The tiers are in the order their talkers first speak."""
    text = Path(file_path).read_text(encoding="utf-8-sig", errors="replace")
    try:
        subtitles = list(srt.parse(text))
    except srt.SRTParseError as error:
        raise ValueError(f"Cannot read {file_path} as an SRT file: {error}") from error

    tiers: dict[str, dict[str, Any]] = {}
    talker: str | None = None
    for subtitle in subtitles:
        words = " ".join(subtitle.content.split())
        named = TALKER_PREFIX.match(words)
        if named and len(named.group(1)) <= SRT_TALKER_MAX_LENGTH:
            talker = named.group(1)
            words = words[named.end() :]
        if not words:
            continue
        name = talker or SRT_NO_TALKER_TIER
        tier = tiers.setdefault(name, {"name": name, "labels": []})
        if talker:
            tier["talker"] = talker
        tier["labels"].append(
            (
                subtitle.start.total_seconds(),
                subtitle.end.total_seconds(),
                words,
            )
        )
    return list(tiers.values())
