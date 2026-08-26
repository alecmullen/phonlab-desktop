import pyqtgraph as pg
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QPainter, QPainterPath, QPicture

V_MARGIN = 0.05
H_MARGIN = 0.075


class NodeView(pg.GraphicsObject):
    def __init__(self, x: float, ys: list[float]):
        super().__init__()
        self.x = x
        self.ys = ys

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

    def paint(self, p, opt, widget):
        p.drawPicture(0, 0, self.pic)

    def boundingRect(self):
        return QRectF(
            -H_MARGIN,
            -V_MARGIN,
            2 * H_MARGIN,
            self.ys[-1] - self.ys[0] + 1 + 2 * V_MARGIN,
        )
