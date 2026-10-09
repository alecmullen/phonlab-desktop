from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from pytestqt.qtbot import QtBot

from ui.main.splash import ClickableSplash


class FakeMainWindow:
    def __init__(self):
        self.open_files_calls = 0

    def open_files(self):
        self.open_files_calls += 1


def test_creates_splash_pixmap_at_default_size(qtbot: QtBot):
    splash = ClickableSplash(FakeMainWindow())

    assert splash.pixmap().width() == 400
    assert splash.pixmap().height() == 300


def test_mouse_press_opens_files_on_main_window(qtbot: QtBot):
    main_window = FakeMainWindow()
    splash = ClickableSplash(main_window)
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(10, 10),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    splash.mousePressEvent(event)

    assert main_window.open_files_calls == 1
