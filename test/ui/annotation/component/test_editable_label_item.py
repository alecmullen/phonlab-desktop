from collections.abc import Iterator

import pyqtgraph as pg
import pytest
from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QFocusEvent, QKeyEvent, QMouseEvent
from pytestqt.qtbot import QtBot

from ui.annotation.component.editable_label_item import EditableLabelItem
from ui.annotation.state.annotation_label_state import AnnotationLabelState

NO_INTERACTION = Qt.TextInteractionFlag.NoTextInteraction
EDITOR_INTERACTION = Qt.TextInteractionFlag.TextEditorInteraction


@pytest.fixture
def plot(qtbot: QtBot) -> Iterator[pg.PlotItem]:
    plot = pg.PlotItem()
    layout = pg.GraphicsLayoutWidget()
    layout.addItem(plot)
    layout.resize(400, 300)
    layout.show()
    qtbot.addWidget(layout)
    qtbot.waitExposed(layout)
    yield plot  # the layout must outlive the test or the view box is deleted


@pytest.fixture
def item(plot: pg.PlotItem) -> EditableLabelItem:
    label = AnnotationLabelState(pos=(0.5, 0.25), size=(1.0, 0.5), label="hello")
    return EditableLabelItem(label, (0.5, 0.5), (0, 0, 0), lambda: None, plot)


def mouse_event(
    event_type: QEvent.Type, button: Qt.MouseButton = Qt.MouseButton.RightButton
) -> QMouseEvent:
    return QMouseEvent(
        event_type,
        QPointF(1, 1),
        QPointF(1, 1),
        button,
        button,
        Qt.KeyboardModifier.NoModifier,
    )


def key_event(
    key: Qt.Key,
    modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
) -> QKeyEvent:
    return QKeyEvent(QEvent.Type.KeyPress, key, modifiers)


def focus_out_event() -> QFocusEvent:
    return QFocusEvent(QEvent.Type.FocusOut, Qt.FocusReason.MouseFocusReason)


def right_click(item: EditableLabelItem):
    item.mousePressEvent(mouse_event(QEvent.Type.MouseButtonPress))
    item.mouseReleaseEvent(mouse_event(QEvent.Type.MouseButtonRelease))


def test_init_stores_label_id_and_text(plot: pg.PlotItem):
    label = AnnotationLabelState(pos=(1.0, 0.5), size=(1.0, 0.5), label="abc")

    item = EditableLabelItem(label, (0.5, 0.5), (0, 0, 0), lambda: None, plot)

    assert item.label_id == label.id
    assert item.toPlainText() == "abc"
    assert (item.pos().x(), item.pos().y()) == (1.0, 0.5)


def test_init_is_not_editable(item: EditableLabelItem):
    assert item.textItem.textInteractionFlags() == NO_INTERACTION
    assert item.text_at_edit_start is None


def test_right_click_makes_label_editable(item: EditableLabelItem):
    right_click(item)

    assert item.textItem.textInteractionFlags() == EDITOR_INTERACTION
    assert item.text_at_edit_start == "hello"


def test_right_press_is_accepted_to_grab_the_mouse(item: EditableLabelItem):
    event = mouse_event(QEvent.Type.MouseButtonPress)
    event.setAccepted(False)

    item.mousePressEvent(event)

    assert event.isAccepted()
    assert item.right_mouse_pressed is True


def test_left_press_is_ignored(item: EditableLabelItem):
    event = mouse_event(QEvent.Type.MouseButtonPress, Qt.MouseButton.LeftButton)

    item.mousePressEvent(event)

    assert not event.isAccepted()
    assert item.right_mouse_pressed is False


def test_right_release_without_press_does_not_edit(item: EditableLabelItem):
    event = mouse_event(QEvent.Type.MouseButtonRelease)

    item.mouseReleaseEvent(event)

    assert not event.isAccepted()
    assert item.textItem.textInteractionFlags() == NO_INTERACTION


def test_left_release_does_not_edit(item: EditableLabelItem):
    item.mousePressEvent(mouse_event(QEvent.Type.MouseButtonPress))
    event = mouse_event(QEvent.Type.MouseButtonRelease, Qt.MouseButton.LeftButton)

    item.mouseReleaseEvent(event)

    assert not event.isAccepted()
    assert item.textItem.textInteractionFlags() == NO_INTERACTION


def test_right_release_resets_pressed_flag(item: EditableLabelItem):
    right_click(item)

    assert item.right_mouse_pressed is False


def test_set_editable_selects_all_text(item: EditableLabelItem):
    item.setEditable(True)

    assert item.textItem.textCursor().selectedText() == "hello"


def test_exit_editing_clears_selection_and_interaction(item: EditableLabelItem):
    item.setEditable(True)

    item.setEditable(False)

    assert item.textItem.textInteractionFlags() == NO_INTERACTION
    assert item.textItem.textCursor().selectedText() == ""
    assert item.text_at_edit_start is None


def test_exit_editing_without_change_does_not_emit(
    qtbot: QtBot, item: EditableLabelItem
):
    item.setEditable(True)

    called = []
    item.on_edit = lambda idx, txt: called.append((idx, txt))

    item.setEditable(False)

    assert called == []


def test_exit_editing_with_change_emits_id_and_text(
    qtbot: QtBot, item: EditableLabelItem
):
    item.setEditable(True)

    called = []
    item.on_edit = lambda idx, txt: called.append((idx, txt))

    item.setPlainText("changed")

    item.setEditable(False)

    assert called == [(item.label_id, "changed")]


@pytest.mark.parametrize(
    "key", [Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Escape]
)
def test_enter_is_consumed_to_finish_editing(item: EditableLabelItem, key: Qt.Key):
    item.setEditable(True)

    assert item.eventFilter(item.textItem, key_event(key)) is True


@pytest.mark.parametrize("key", [Qt.Key.Key_Return, Qt.Key.Key_Enter])
def test_shift_enter_is_passed_through_for_newline(
    item: EditableLabelItem, key: Qt.Key
):
    item.setEditable(True)

    handled = item.eventFilter(
        item.textItem, key_event(key, Qt.KeyboardModifier.ShiftModifier)
    )

    assert handled is False


def test_other_keys_are_passed_through(item: EditableLabelItem):
    item.setEditable(True)

    assert item.eventFilter(item.textItem, key_event(Qt.Key.Key_A)) is False


def test_focus_out_commits_edit(qtbot: QtBot, item: EditableLabelItem):
    item.setEditable(True)

    called = []
    item.on_edit = lambda idx, txt: called.append((idx, txt))

    item.setPlainText("changed")

    handled = item.eventFilter(item.textItem, focus_out_event())

    assert handled is True
    assert called == [(item.label_id, "changed")]


def test_focus_out_without_change_does_not_call_on_edit(
    qtbot: QtBot, item: EditableLabelItem
):
    item.setEditable(True)

    called = []
    item.on_edit = lambda idx, txt: called.append((idx, txt))

    item.eventFilter(item.textItem, focus_out_event())

    assert called == []


def test_event_filter_ignores_none_event(item: EditableLabelItem):
    assert item.eventFilter(item.textItem, None) is False
