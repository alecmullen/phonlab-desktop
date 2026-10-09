"""Generate icons/phonlab.ico and icons/phonlab.icns from icons/phonlab.png."""

from pathlib import Path

from PIL import Image

ICON_DIR = Path(__file__).resolve().parent.parent / "icons"

with Image.open(ICON_DIR / "phonlab.png") as png:
    png = png.convert("RGBA")
    png.save(
        ICON_DIR / "phonlab.ico",
        sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)],
    )
    png.resize((1024, 1024), Image.LANCZOS).save(ICON_DIR / "phonlab.icns")
