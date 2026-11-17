import importlib.resources
import logging
import os
import sys
from pathlib import Path
from typing import cast

import phonlab  # noqa: F401
from platformdirs import PlatformDirs
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from bootstrap.view_model_factory_impl import ViewModelFactoryImpl
from res.constants import DOUBLE_CLICK_INTERVAL_MS
from ui.main.component.open_project_dialog import OpenProjectDialog, icon_path
from ui.main.main_window import MainWindow

if getattr(sys, "frozen", False):
    # Create and set numba cache
    _numba_cache_dir = os.path.join(os.path.dirname(sys.executable), "numba_cache")
    os.makedirs(_numba_cache_dir, exist_ok=True)
    os.environ.setdefault("NUMBA_CACHE_DIR", _numba_cache_dir)

    # Set up error logs
    log_dir = Path(PlatformDirs("Phonlab").user_log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_dir / "phonlab.log",
        level=logging.ERROR,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

logger = logging.getLogger(__name__)

try:
    import librosa

    example_audio = (
        importlib.resources.files("phonlab")
        / "data"
        / "example_audio"
        / "two_plus_two.wav"
    )
    librosa.load(cast(os.PathLike, example_audio))
except FileNotFoundError:
    logger.exception("Example file not found. Librosa JIT functions not pre-compiled.")

if os.environ.get("PHONLAB_WARMUP_ONLY"):
    # Used by CI to force the numba compile above and populate numba_cache/
    # right after a fresh build, without spinning up the Qt event loop.
    sys.exit(0)

if __name__ == "__main__":

    def run_app():
        app = QApplication(sys.argv)
        app.setWindowIcon(QIcon(str(icon_path())))
        app.setDoubleClickInterval(DOUBLE_CLICK_INTERVAL_MS)

        mainWin = MainWindow(ViewModelFactoryImpl())

        # Create and show splash screen
        splash = OpenProjectDialog(mainWin)
        mainWin.splash = splash

        mainWin.show()
        splash.show()

        # Optionally open a file if provided as command line argument
        if len(sys.argv) > 1:
            mainWin.open_single_document(sys.argv[1:])

        app.exec()

    run_app()
