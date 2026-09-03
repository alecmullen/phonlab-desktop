import importlib
import logging
import os
import sys
import phonlab

from PyQt6.QtWidgets import QApplication

from ui.main.main_window import MainWindow
from ui.main.splash import ClickableSplash, create_splash_pixmap

logger = logging.getLogger(__name__)

if getattr(sys, "frozen", False):
    # Create and set numba cache
    _numba_cache_dir = os.path.join(os.path.dirname(sys.executable), "numba_cache")
    os.makedirs(_numba_cache_dir, exist_ok=True)
    os.environ.setdefault("NUMBA_CACHE_DIR", _numba_cache_dir)
else:
    # Only relevant when running from source: a packaged .app (built with
    # `pyinstaller --name Phonlab`) already has its own Info.plist and shows
    # "Phonlab" in the macOS menu bar correctly. Run unbundled via `python
    # phonlab_desktop.py`, though, and macOS shows the interpreter's own
    # process name ("Python") there instead — this is a best-effort,
    # dev-only fix for that, silently doing nothing if pyobjc isn't
    # installed or we're not on macOS.
    if sys.platform == "darwin":
        try:
            from Foundation import NSBundle

            info = NSBundle.mainBundle().localizedInfoDictionary() or NSBundle.mainBundle().infoDictionary()
            if info is not None:
                info["CFBundleName"] = "Phonlab"
        except ImportError:
            pass

try:
    import librosa
    example_audio = (
        importlib.resources.files("phonlab")
        / "data"
        / "example_audio"
        / "two_plus_two.wav"
    )
    librosa.load(example_audio)
except FileNotFoundError:
    logger.exception("Example file not found. Librosa JIT functions not pre-compiled.")

if os.environ.get("PHONLAB_WARMUP_ONLY"):
    # Used by CI to force the numba compile above and populate numba_cache/
    # right after a fresh build, without spinning up the Qt event loop.
    sys.exit(0)

if __name__ == "__main__":

    def run_app():
        app = QApplication(sys.argv)

        mainWin = MainWindow()

        # Create and show splash screen
        splash_pix = create_splash_pixmap()
        splash = ClickableSplash(splash_pix, mainWin)
        mainWin.splash = splash

        mainWin.show()
        splash.show()

        # Optionally open a file if provided as command line argument
        if len(sys.argv) > 1:
            mainWin.open_file(sys.argv[1])

        app.exec()

    run_app()
