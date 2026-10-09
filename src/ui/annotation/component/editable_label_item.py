from collections.abc import Callable
from typing import cast

import pyqtgraph as pg
from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import (
    QFont,
    QFontMetrics,
    QKeyEvent,
    QMouseEvent,
    QTextCursor,
    QTextOption,
)

from res.constants import POINT_LABEL_WIDTH
from ui.annotation.state.annotation_label_state import AnnotationLabelState


class EditableLabelItem(pg.TextItem):
    """
    A custom pyqtgraph TextItem that becomes editable on a double-click.
    """

    def __init__(
        self,
        label: AnnotationLabelState,
        anchor: tuple[float, float],
        color: tuple[int, int, int],
        on_edit: Callable[[int, str], None],
        parent_plot: pg.PlotItem,
    ):
        pixel_size = parent_plot.getViewBox().viewPixelSize()

        label_width = int(label.size[0] / pixel_size[0])
        label_height = int(label.size[1] / pixel_size[1])

        if label_width == 0:
            label_width = POINT_LABEL_WIDTH

        text = " ".join(label.label.splitlines())

        font = QFont("Arial", 16)
        metrics = QFontMetrics(font)
        num_lines = int(label_height / (metrics.lineSpacing() * 1.5))
        clipped_text = metrics.elidedText(
            text, Qt.TextElideMode.ElideRight, label_width * num_lines
        )

        super().__init__(text=clipped_text, anchor=anchor, color=color)

        self.label_id = label.id

        option = self.textItem.document().defaultTextOption()
        option.setWrapMode(QTextOption.WrapMode.WordWrap)
        option.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.textItem.document().setDefaultTextOption(option)
        self.setFont(font)
        self.setTextWidth(label_width)
        self.setPos(*label.pos)

        self.textItem.installEventFilter(self)

        self.on_edit = on_edit

        self.right_mouse_pressed: bool = False
        self.text_at_edit_start: str | None = None

    def mousePressEvent(self, a0: QMouseEvent | None):
        if a0 is None:
            return
        if a0.button() == Qt.MouseButton.RightButton:
            self.right_mouse_pressed = True
            a0.accept()
        else:
            a0.ignore()

    def mouseReleaseEvent(self, a0: QMouseEvent | None):
        if a0 is None:
            return
        if a0.button() == Qt.MouseButton.RightButton and self.right_mouse_pressed:
            self.setEditable(True)
            a0.accept()
            self.right_mouse_pressed = False
        else:
            a0.ignore()

    def setEditable(self, editable: bool):
        if editable:
            self.text_at_edit_start = self.textItem.toPlainText()
            self.textItem.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditorInteraction
            )
            self.textItem.setFocus()

            cursor = self.textItem.textCursor()
            cursor.select(QTextCursor.SelectionType.Document)
            self.textItem.setTextCursor(cursor)
        else:
            start_text = self.text_at_edit_start
            self.text_at_edit_start = None

            self.textItem.setTextInteractionFlags(
                Qt.TextInteractionFlag.NoTextInteraction
            )

            cursor = self.textItem.textCursor()
            cursor.clearSelection()
            self.textItem.setTextCursor(cursor)

            self.textItem.clearFocus()

            new_text = self.textItem.toPlainText()
            if new_text != start_text:
                self.on_edit(self.label_id, new_text)

    def eventFilter(self, a0: QObject | None, a1: QEvent | None) -> bool:
        event = a1
        if event is None:
            return False
        if event.type() == QEvent.Type.KeyPress:
            event = cast(QKeyEvent, event)
            if (
                event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            ) or event.key() == Qt.Key.Key_Escape:
                self.textItem.clearFocus()
                event.accept()
                return True
        if event.type() == QEvent.Type.FocusOut:
            self.setEditable(False)
            event.accept()
            return True
        event.ignore()
        return False
