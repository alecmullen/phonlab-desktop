from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow
from pytestqt.qtbot import QtBot

from ui.main.component.open_project_dialog import OpenProjectDialog


class FakeMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.select_path_calls = 0

    def select_path_to_open(self):
        self.select_path_calls += 1


def test_creates_splash_pixmap_at_default_size(qtbot: QtBot):
    main_window = FakeMainWindow()
    qtbot.addWidget(main_window)
    splash = OpenProjectDialog(main_window)

    assert splash.label.pixmap().width() == 400
    assert splash.label.pixmap().height() == 300


def test_clicking_the_card_selects_a_project_or_file_on_main_window(qtbot: QtBot):
    main_window = FakeMainWindow()
    qtbot.addWidget(main_window)
    splash = OpenProjectDialog(main_window)
    qtbot.addWidget(splash)

    qtbot.mouseClick(splash, Qt.MouseButton.LeftButton)

    assert main_window.select_path_calls == 1


def test_right_click_does_not_open(qtbot: QtBot):
    main_window = FakeMainWindow()
    qtbot.addWidget(main_window)
    splash = OpenProjectDialog(main_window)
    qtbot.addWidget(splash)

    qtbot.mouseClick(splash, Qt.MouseButton.RightButton)

    assert main_window.select_path_calls == 0
