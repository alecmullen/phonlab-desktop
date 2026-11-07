import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QLabel, QPushButton, QWidget

from ui.main.main_window import MainWindow


def icon_path() -> Path:
    """Locate icons/phonlab.png in a source checkout or a PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parents[4]
    return base / "icons" / "phonlab.png"


class OpenProjectDialog(QWidget):
    """Splash screen that opens file dialog when clicked"""

    def __init__(self, main_window: MainWindow):
        super().__init__(main_window, Qt.WindowType.Tool)
        self.main_window = main_window

        self.label = QLabel(self)
        pixmap = self.create_splash_pixmap()
        self.label.setPixmap(pixmap)
        self.setFixedSize(pixmap.width(), pixmap.height())

        button_style = """
            QPushButton {
                min-height: 20px;
                padding: 5px 8px; 
                font-size: 14px;
                color: #212121;
                background: #e7e7e7;
                border: 1px solid darkgray;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #d7d7d7;
            }
            QPushButton:pressed {
                background: #c7c7c7;
            }
        """

        self.open_proj_btn = QPushButton(self.tr("Open a project directory"), self)
        self.open_file_btn = QPushButton(self.tr("Select files (.wav and .TextGrid)"), self)

        font = QFont("Arial", 14)
        self.open_proj_btn.setFont(font)
        self.open_file_btn.setFont(font)
        self.open_proj_btn.setStyleSheet(button_style)
        self.open_file_btn.setStyleSheet(button_style)

        self.open_proj_btn.move(35, 190)
        self.open_file_btn.move(35, 235)

        self.open_proj_btn.clicked.connect(self.main_window.select_project_to_open)
        self.open_file_btn.clicked.connect(self.main_window.select_files_to_open)

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

        painter.end()
        return pixmap
