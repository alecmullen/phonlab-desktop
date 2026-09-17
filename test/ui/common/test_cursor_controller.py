from PyQt6.QtCore import QObject
from pytestqt.qtbot import QtBot

from ui.common.cursor_controller import CursorController


class CursorControllerHost(QObject, CursorController):
    def __init__(self):
        QObject.__init__(self)
        CursorController.__init__(self)


def test_cursor_controller_starts_with_cursor_control(qtbot: QtBot):
    controller = CursorControllerHost()

    assert controller.has_cursor_control is True


def test_remove_cursor_control_clears_flag_and_starts_timer(qtbot: QtBot):
    controller = CursorControllerHost()

    controller.remove_cursor_control()

    assert controller.has_cursor_control is False
    assert controller.cursor_control_timer.isActive() is True


def test_regain_cursor_control_sets_flag_true(qtbot: QtBot):
    controller = CursorControllerHost()
    controller.remove_cursor_control()

    controller.regain_cursor_control()

    assert controller.has_cursor_control is True


def test_cursor_control_timer_automatically_regains_control(qtbot: QtBot):
    controller = CursorControllerHost()

    controller.remove_cursor_control()
    assert controller.has_cursor_control is False

    with qtbot.waitSignal(controller.cursor_control_timer.timeout, timeout=1000):
        pass

    assert controller.has_cursor_control is True
