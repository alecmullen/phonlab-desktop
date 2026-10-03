from PyQt6.QtGui import QPalette
from pytestqt.qtbot import QtBot

from ui.common.context_menu_hint import ContextMenuHint, ContextMenuHintAction


def test_renders_action_text_in_title_label(qtbot: QtBot):
    widget = ContextMenuHint("Copy")
    qtbot.addWidget(widget)

    assert widget.label_title.text() == "Copy"


def test_renders_hint_text_when_provided(qtbot: QtBot):
    widget = ContextMenuHint("Copy", "Ctrl+C")
    qtbot.addWidget(widget)

    assert widget.label_hint.text() == "Ctrl+C"
    assert widget.label_hint.styleSheet() == "color: gray;"
    assert hasattr(widget, "spacer")


def test_omits_hint_label_when_not_provided(qtbot: QtBot):
    widget = ContextMenuHint("Copy")
    qtbot.addWidget(widget)

    assert not hasattr(widget, "label_hint")
    assert not hasattr(widget, "spacer")


def test_enter_event_highlights_widget(qtbot: QtBot):
    widget = ContextMenuHint("Copy")
    qtbot.addWidget(widget)

    widget.enterEvent(None)

    assert widget.backgroundRole() == QPalette.ColorRole.Highlight
    assert widget.autoFillBackground() is True


def test_leave_event_unhighlights_widget(qtbot: QtBot):
    widget = ContextMenuHint("Copy")
    qtbot.addWidget(widget)
    widget.enterEvent(None)

    widget.leaveEvent(None)

    assert widget.backgroundRole() == QPalette.ColorRole.Window
    assert widget.autoFillBackground() is False


def test_action_stores_text_and_hint(qtbot: QtBot):
    action = ContextMenuHintAction("Copy", "Ctrl+C")

    assert action.action_text == "Copy"
    assert action.hint_text == "Ctrl+C"


def test_action_create_widget_builds_context_menu_hint_with_same_text(qtbot: QtBot):
    action = ContextMenuHintAction("Copy", "Ctrl+C")

    widget = action.createWidget(None)
    qtbot.addWidget(widget)

    assert isinstance(widget, ContextMenuHint)
    assert widget.label_title.text() == "Copy"
    assert widget.label_hint.text() == "Ctrl+C"
