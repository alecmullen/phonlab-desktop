from pathlib import Path
from typing import Any

import soundfile as sf

from core.read_tiers.sibling_file import find_sibling
from res.constants import TIMIT_DEFAULT_SAMPLE_RATE


def read_timit_tiers(words_path: str) -> list[dict[str, Any]]:
    """Reads a TIMIT .wrd file, and the .phn file next to it if there is one, into a
    `word` tier and a `phone` tier. The files give times in samples, so the sample
    rate is read from the sound file next to them (16 kHz if there is none)."""
    sample_rate = _sample_rate(words_path)
    tiers = [{"name": "word", "labels": _read_labels(words_path, sample_rate)}]

    phones_path = find_sibling(words_path, ".phn")
    if phones_path is not None:
        tiers.append(
            {"name": "phone", "labels": _read_labels(phones_path, sample_rate)}
        )
    return tiers


def _sample_rate(path: str) -> int:
    for ext in (".wav", ".sph"):
        audio = find_sibling(path, ext)
        if audio is None:
            continue
        try:
            return int(sf.info(audio).samplerate)
        except (RuntimeError, ValueError):
            continue
    return TIMIT_DEFAULT_SAMPLE_RATE


def _read_labels(path: str, sample_rate: int) -> list[tuple[float, float, str]]:
    labels: list[tuple[float, float, str]] = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip() == "":
            continue
        fields = line.split()
        try:
            begin, end = int(fields[0]), int(fields[1])
            text = " ".join(fields[2:])
        except (ValueError, IndexError) as err:
            raise ValueError(f"Cannot read line of {path}: {line!r}") from err
        labels.append((begin / sample_rate, end / sample_rate, text))
    return labels
