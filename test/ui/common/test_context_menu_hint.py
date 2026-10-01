from pytestqt.qtbot import QtBot

from ui.common.context_menu_hint import ContextMenuHintAction


def test_action_without_hint_uses_plain_text(qtbot: QtBot):
    action = ContextMenuHintAction("Copy")

    assert action.text() == "Copy"


def test_action_with_hint_separates_hint_with_tab(qtbot: QtBot):
    action = ContextMenuHintAction("Copy", "Ctrl+C")

    assert action.text() == "Copy\tCtrl+C"
