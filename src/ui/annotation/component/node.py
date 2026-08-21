import pyqtgraph as pg
from pyqtgraph import QtCore, QtGui


class Node(pg.GraphicsObject):
    def __init__(self, x: float, ys: list[float]):
        super().__init__()
        self.x = x
        self.ys = ys

        y_last = ys[0]
        circle = pg.PlotDataItem([x], [y_last], symbol="o", symbolPen="b")
        circle.setParentItem(self)

        self.pic = QtGui.QPicture()
        self._generate_picture()

    def _generate_picture(self):
        self.prepareGeometryChange()
        painter = QtGui.QPainter(self.pic)

        solid_path = QtGui.QPainterPath()
        dotted_path = QtGui.QPainterPath()
        started = False
        for y in self.ys:
            if started and solid_path.currentPosition().y() != y:
                dotted_path.moveTo(self.x, solid_path.currentPosition().y())
                dotted_path.lineTo(self.x, y)
            solid_path.moveTo(self.x, y)
            solid_path.lineTo(self.x, y+1)

            started = True

        pen = pg.mkPen(color="b", width=3)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.FlatCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)

        painter.setPen(pen)
        painter.drawPath(solid_path)

        pen = pg.mkPen("b", width=3)
        pen.setStyle(QtCore.Qt.PenStyle.DotLine)
        pen.setDashPattern([1, 4])
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)

        painter.setPen(pen)
        painter.drawPath(dotted_path)

        painter.end()

    def paint(self, p, opt, widget):
        p.drawPicture(0, 0, self.pic)
        
    def boundingRect(self):
        return QtCore.QRectF(self.pic.boundingRect())
                    