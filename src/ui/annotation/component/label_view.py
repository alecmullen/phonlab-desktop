from collections.abc import Callable

import pyqtgraph as pg
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QPainter, QPicture
from PyQt6.QtWidgets import QStyleOptionGraphicsItem, QWidget

from ui.annotation.component.editable_label_item import EditableLabelItem
from ui.annotation.state.annotation_label_state import AnnotationLabelState


class LabelView(pg.GraphicsObject):
    def __init__(
        self,
        parent_plot: pg.PlotItem,
        labels: list[AnnotationLabelState],
        on_edit_label: Callable[[int, str], None],
    ):
        super().__init__()
        self.labels = labels

        self.view_rect: QRectF = parent_plot.getViewBox().viewRect()
        self.setPos(self.view_rect.left(), self.view_rect.bottom())

        for label in labels:
            label_item = EditableLabelItem(
                label, (0.5, 0.5), (0, 0, 0), on_edit_label, parent_plot
            )
            label_item.setParentItem(self)

        self.pic = QPicture()
        self._generate_picture()

    def _generate_picture(self):
        painter = QPainter(self.pic)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(pg.mkBrush(0, 0, 0, 20))
        for label in self.labels:
            width, height = label.size
            painter.drawRect(
                QRectF(
                    label.pos[0] - (width / 2),
                    label.pos[1] - (height / 2),
                    width,
                    height,
                )
            )
        painter.end()

    def paint(
        self,
        painter: QPainter | None,
        option: QStyleOptionGraphicsItem | None,
        widget: QWidget | None,
    ):
        if painter is not None:
            painter.drawPicture(0, 0, self.pic)

    def boundingRect(self) -> QRectF:
        return self.view_rect
