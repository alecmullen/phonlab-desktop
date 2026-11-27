from pathlib import Path

from support.audio_files import write_wavs

SIMPLE_TEXTGRID = """File type = "ooTextFile"
Object class = "TextGrid"
xmin = 0
xmax = 1.0
tiers? <exists>
size = 1
item []:
    item [1]:
        class = "IntervalTier"
        name = "word"
        xmin = 0
        xmax = 1.0
        intervals: size = 2
        intervals [1]:
            xmin = 0
            xmax = 0.5
            text = "hello"
        intervals [2]:
            xmin = 0.5
            xmax = 1.0
            text = "world"
"""


def write_simple_textgrid(path: Path) -> str:
    path.write_text(SIMPLE_TEXTGRID)
    return str(path)


def word_and_phone_textgrid() -> str:
    """A TextGrid whose word tier and phone tier share their boundaries: the words
    "hi" and "yo", each of two phones"""

    def tier(index: int, name: str, items: list[tuple[float, float, str]]) -> str:
        text = (
            f'    item [{index}]:\n        class = "IntervalTier"\n'
            f'        name = "{name}"\n        xmin = 0\n        xmax = 1\n'
            f"        intervals: size = {len(items)}\n"
        )
        for number, (begin, end, label) in enumerate(items, 1):
            text += (
                f"        intervals [{number}]:\n            xmin = {begin}\n"
                f'            xmax = {end}\n            text = "{label}"\n'
            )
        return text

    words = [(0, 0.5, "hi"), (0.5, 1, "yo")]
    phones = [(0, 0.25, "h"), (0.25, 0.5, "i"), (0.5, 0.75, "y"), (0.75, 1, "o")]
    return (
        'File type = "ooTextFile"\nObject class = "TextGrid"\nxmin = 0\nxmax = 1\n'
        "tiers? <exists>\nsize = 2\nitem []:\n"
        + tier(1, "word", words)
        + tier(2, "phone", phones)
    )


def textgrid_project(root: Path) -> Path:
    """Two talkers' folders, two recordings each, all annotated"""
    for t in ("aa1", "bb2"):
        for n in (1, 2):
            # of different lengths, so that they are not taken for channels of one
            write_wavs(root, [f"{t}/{t}_0{n}.wav"], frames=100 * n)
            (root / t / f"{t}_0{n}.TextGrid").write_text(word_and_phone_textgrid())
    return root
