from PyQt6.QtWidgets import QMainWindow
from pytestqt.qtbot import QtBot

from ui.main.component.open_project_dialog import OpenProjectDialog


class FakeMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.select_project_calls = 0
        self.select_files_calls = 0

    def select_project_to_open(self):
        self.select_project_calls += 1

    def select_files_to_open(self):
        self.select_files_calls += 1


def test_creates_splash_pixmap_at_default_size(qtbot: QtBot):
    main_window = FakeMainWindow()
    qtbot.addWidget(main_window)
    splash = OpenProjectDialog(main_window)

    assert splash.label.pixmap().width() == 400
    assert splash.label.pixmap().height() == 300


def test_open_project_button_selects_project_on_main_window(qtbot: QtBot):
    main_window = FakeMainWindow()
    qtbot.addWidget(main_window)
    splash = OpenProjectDialog(main_window)

    splash.open_proj_btn.click()

    assert main_window.select_project_calls == 1
    assert main_window.select_files_calls == 0


def test_select_files_button_selects_files_on_main_window(qtbot: QtBot):
    main_window = FakeMainWindow()
    qtbot.addWidget(main_window)
    splash = OpenProjectDialog(main_window)

    splash.open_file_btn.click()

    assert main_window.select_files_calls == 1
    assert main_window.select_project_calls == 0
