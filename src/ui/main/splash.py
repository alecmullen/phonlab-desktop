import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QMouseEvent, QPainter, QPixmap
from PyQt6.QtWidgets import QSplashScreen

from ui.main.main_window import MainWindow


def _icon_path() -> Path:
    """Locate icons/phonlab.png in a source checkout or a PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parents[3]
    return base / "icons" / "phonlab.png"


class ClickableSplash(QSplashScreen):
    """Splash screen that opens file dialog when clicked"""

    def __init__(self, main_window: MainWindow):
        pixmap = self.create_splash_pixmap()
        super().__init__(pixmap, Qt.WindowType.Tool)
        self.main_window = main_window

    def mousePressEvent(self, a0: QMouseEvent | None):
        """Open file dialog when splash is clicked"""
        self.main_window.open_files()
        super().mousePressEvent(a0)

    def create_splash_pixmap(self, width: int = 400, height: int = 300) -> QPixmap:
        """Create a simple splash screen pixmap"""
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.white)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw border
        painter.setPen(Qt.GlobalColor.darkGray)
        painter.drawRect(0, 0, width - 1, height - 1)

        # Draw icon, top center
        icon = QPixmap(str(_icon_path()))
        if not icon.isNull():
            icon = icon.scaledToHeight(
                90, Qt.TransformationMode.SmoothTransformation
            )
            painter.drawPixmap((width - icon.width()) // 2, 15, icon)

        # Draw title
        title_font = QFont("Arial", 24, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(0, 115, width, 50, Qt.AlignmentFlag.AlignCenter, "Phonlab")

        # Draw instruction
        instruction_font = QFont("Arial", 16)
        painter.setFont(instruction_font)
        painter.setPen(Qt.GlobalColor.darkGray)
        painter.drawText(
            0,
            190,
            width,
            30,
            Qt.AlignmentFlag.AlignCenter,
            self.tr("Click on this card to open a sound file"),
        )

        painter.end()
        return pixmap
