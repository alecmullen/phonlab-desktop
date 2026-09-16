import pyqtgraph as pg
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QFont, QPainter, QPicture
from PyQt6.QtWidgets import QStyleOptionGraphicsItem, QWidget

from ui.annotation.state.label_view_state import LabelViewState


class LabelView(pg.GraphicsObject):
    def __init__(self, labels: list[LabelViewState], parent_plot: pg.PlotItem):
        super().__init__()
        self.labels = labels
        self.parent_plot = parent_plot

        for label in labels:
            label_item = pg.TextItem(label.label, anchor=(0.5, 0.5), color=(0, 0, 0))
            label_item.setFont(QFont("Arial", 16))
            label_item.setPos(*label.pos)
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
        return self.parent_plot.getViewBox().rect()
