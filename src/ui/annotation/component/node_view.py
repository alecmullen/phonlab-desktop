import pyqtgraph as pg
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QPainter, QPainterPath, QPicture
from PyQt6.QtWidgets import QStyleOptionGraphicsItem, QWidget

V_MARGIN = 7
H_MARGIN = 5


class NodeView(pg.GraphicsObject):
    def __init__(self, x: float, ys: list[float], pixel_size: tuple[float, float]):
        super().__init__()
        self.x = x
        self.ys = ys
        self.pixel_size = pixel_size

        self.setPos(x, ys[0])

        circle = pg.PlotDataItem([0], [0], symbol="o", symbolPen="b", symbolSize=8)
        circle.setParentItem(self)

        self.pic = QPicture()
        self._generate_picture()

    def _generate_picture(self):
        self.prepareGeometryChange()
        painter = QPainter(self.pic)

        solid_path = QPainterPath()
        dotted_path = QPainterPath()
        started = False
        for y in [y - self.ys[0] for y in self.ys]:
            if started and solid_path.currentPosition().y() != y:
                dotted_path.moveTo(0, solid_path.currentPosition().y())
                dotted_path.lineTo(0, y)
            solid_path.moveTo(0, y)
            solid_path.lineTo(0, y + 1)

            started = True

        pen = pg.mkPen(color="b", width=3)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

        painter.setPen(pen)
        painter.drawPath(solid_path)

        pen = pg.mkPen("b", width=3)
        pen.setStyle(Qt.PenStyle.DotLine)
        pen.setDashPattern([1, 4])
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

        painter.setPen(pen)
        painter.drawPath(dotted_path)

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
        return QRectF(
            -H_MARGIN * self.pixel_size[0],
            -V_MARGIN * self.pixel_size[1],
            2 * H_MARGIN * self.pixel_size[0],
            self.ys[-1] - self.ys[0] + 1 + 2 * V_MARGIN * self.pixel_size[1],
        )
