from PyQt6.QtCore import QTimer, pyqtSlot


class CursorController:
    def __init__(self):
        self.has_cursor_control = True

        self.cursor_control_timer = QTimer()
        self.cursor_control_timer.setInterval(150)
        self.cursor_control_timer.setSingleShot(True)
        self.cursor_control_timer.timeout.connect(self.regain_cursor_control)

    @pyqtSlot()
    def regain_cursor_control(self):
        self.has_cursor_control = True

    def remove_cursor_control(self):
        self.has_cursor_control = False
        self.cursor_control_timer.start()
