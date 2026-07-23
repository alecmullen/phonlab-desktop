from PyQt6.QtGui import QPixmap, QPainter, QFont
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSplashScreen

class ClickableSplash(QSplashScreen):
    """Splash screen that opens file dialog when clicked"""
    
    def __init__(self, pixmap, main_window):
        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint)
        self.main_window = main_window
    
    def mousePressEvent(self, event):
        """Open file dialog when splash is clicked"""
        self.main_window.open_file()
        super().mousePressEvent(event)


def create_splash_pixmap(width=400, height=300):
    """Create a simple splash screen pixmap"""
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.white)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Draw border
    painter.setPen(Qt.GlobalColor.darkGray)
    painter.drawRect(0, 0, width-1, height-1)
    
    # Draw title
    title_font = QFont("Arial", 24, QFont.Weight.Bold)
    painter.setFont(title_font)
    painter.setPen(Qt.GlobalColor.black)
    painter.drawText(0, 80, width, 50, Qt.AlignmentFlag.AlignCenter, "Phonlab")
    
    # Draw instruction
    instruction_font = QFont("Arial", 16)
    painter.setFont(instruction_font)
    painter.setPen(Qt.GlobalColor.darkGray)
    painter.drawText(0, 160, width, 30, Qt.AlignmentFlag.AlignCenter, "Click on this card to open a sound file")
    
    painter.end()
    return pixmap
