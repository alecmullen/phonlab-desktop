import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QMouseEvent, QPainter, QPixmap
from PyQt6.QtWidgets import QLabel, QWidget

from ui.main.main_window import MainWindow


def icon_path() -> Path:
    """Locate icons/phonlab.png in a source checkout or a PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parents[4]
    return base / "icons" / "phonlab.png"


class OpenProjectDialog(QWidget):
    """Splash screen card that opens the dialog to open a project or file when clicked"""

    def __init__(self, main_window: MainWindow):
        super().__init__(main_window, Qt.WindowType.Tool)
        self.main_window = main_window

        self.label = QLabel(self)
        pixmap = self.create_splash_pixmap()
        self.label.setPixmap(pixmap)
        self.setFixedSize(pixmap.width(), pixmap.height())

        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, a0: QMouseEvent | None):
        """Clicking anywhere on the card opens the dialog to open a project or file"""
        if a0 is not None and a0.button() == Qt.MouseButton.LeftButton:
            self.main_window.select_path_to_open()

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
        icon = QPixmap(str(icon_path()))
        if not icon.isNull():
            icon = icon.scaledToHeight(90, Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap((width - icon.width()) // 2, 15, icon)

        # Draw title
        title_font = QFont("Arial", 24, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(0, 115, width, 50, Qt.AlignmentFlag.AlignCenter, "Phonlab")

        # Draw the instruction
        painter.setFont(QFont("Arial", 14))
        painter.setPen(Qt.GlobalColor.darkGray)
        painter.drawText(
            0,
            200,
            width,
            40,
            Qt.AlignmentFlag.AlignCenter,
            self.tr("Click this card to open a file or project"),
        )

        painter.end()
        return pixmap
