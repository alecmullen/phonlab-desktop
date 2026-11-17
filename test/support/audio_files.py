from pathlib import Path

import numpy as np
import soundfile as sf


def write_wavs(root: Path, paths: list[str], frames: int = 100, fs: int = 8000) -> Path:
    """Writes a short mono wav file at every relative path"""
    for path in paths:
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        sf.write(file, np.zeros(frames), fs)
    return root


def textgrid_with_tiers(tier_names: list[str]) -> str:
    """A TextGrid with an interval tier of that name, holding one word, for each"""
    tiers = ""
    for index, name in enumerate(tier_names, start=1):
        tiers += f"""    item [{index}]:
        class = "IntervalTier"
        name = "{name}"
        xmin = 0
        xmax = 1.0
        intervals: size = 1
        intervals [1]:
            xmin = 0
            xmax = 1.0
            text = "hi"
"""
    return f"""File type = "ooTextFile"
Object class = "TextGrid"
xmin = 0
xmax = 1.0
tiers? <exists>
size = {len(tier_names)}
item []:
{tiers}"""
