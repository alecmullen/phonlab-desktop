import sys

from PyQt6.QtWidgets import QApplication

from ui.view.main_window import MainWindow
from ui.view.splash import ClickableSplash, create_splash_pixmap

if __name__ == "__main__":
    def run_app():
        app = QApplication(sys.argv)

        mainWin = MainWindow()

        # Create and show splash screen
        splash_pix = create_splash_pixmap()
        splash = ClickableSplash(splash_pix,mainWin)
        mainWin.splash = splash
        
        splash.show()
        app.processEvents()
        mainWin.show()
        
        # Optionally open a file if provided as command line argument
        if len(sys.argv) > 1:
            mainWin.open_file(sys.argv[1])
        
        app.exec()
    run_app()
