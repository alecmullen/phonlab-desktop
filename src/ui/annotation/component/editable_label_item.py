import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import (
    QFocusEvent,
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

    editing_finished = pyqtSignal(int, str)

    def __init__(
        self,
        label: AnnotationLabelState,
        anchor: tuple[float, float],
        color: tuple[int, int, int],
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

    def mouseDoubleClickEvent(self, a0: QMouseEvent | None):
        if a0 is None:
            return
        if a0.button() == Qt.MouseButton.LeftButton:
            self.setEditable(True)
            a0.accept()
        else:
            super().mouseDoubleClickEvent(a0)

    def setEditable(self, editable: bool):
        if editable:
            self.textItem.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextEditorInteraction
            )
            self.textItem.setFocus()

            cursor = self.textItem.textCursor()
            cursor.select(QTextCursor.SelectionType.Document)
            self.textItem.setTextCursor(cursor)
        else:
            self.textItem.setTextInteractionFlags(
                Qt.TextInteractionFlag.NoTextInteraction
            )
            self.textItem.clearFocus()

            self.editing_finished.emit(self.label_id, self.textItem.toPlainText())

    def focusOutEvent(self, a0: QFocusEvent | None):
        # Save changes when the user clicks away
        self.setEditable(False)
        super().focusOutEvent(a0)

    def keyPressEvent(self, a0: QKeyEvent | None):
        # Stop editing if user presses Enter/Return (without Shift) or Escape
        if a0 is None:
            return
        if a0.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if not (a0.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                self.setEditable(False)
                a0.accept()
                return
        elif a0.key() == Qt.Key.Key_Escape:
            self.setEditable(False)
            a0.accept()
            return

        super().keyPressEvent(a0)
