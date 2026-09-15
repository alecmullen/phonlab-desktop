import pyqtgraph as pg
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QFont, QPainter, QPicture
from PyQt6.QtWidgets import QStyleOptionGraphicsItem, QWidget


class LabelView(pg.GraphicsObject):
    def __init__(self, size: tuple, label: str):
        super().__init__()
        self.size = size
        self.label = label

        label_item = pg.TextItem(self.label, anchor=(0.5, 0.5), color=(0, 0, 0))
        label_item.setFont(QFont("Arial", 16))
        label_item.setPos(0, 0)
        label_item.setParentItem(self)

        self.pic = QPicture()
        self._generate_picture()

    def _generate_picture(self):
        width, height = self.size

        painter = QPainter(self.pic)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(pg.mkBrush(0, 0, 0, 20))
        painter.drawRect(QRectF(-width / 2, -height / 2, width, height))
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
        width, height = self.size
        return QRectF(-width / 2, -height / 2, width, height)
