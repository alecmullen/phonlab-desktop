import importlib
import logging
import sys

import librosa
from PyQt6.QtWidgets import QApplication

from ui.main.main_window import MainWindow
from ui.main.splash import ClickableSplash, create_splash_pixmap

logger = logging.getLogger(__name__)

try:
    example_audio = importlib.resources.files('phonlab') / 'data' / 'example_audio' / 'two_plus_two.wav'
    librosa.load(example_audio)
except FileNotFoundError:
    logger.exception("Example file not found. Librosa JIT funcitons not pre-compiled.")

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
