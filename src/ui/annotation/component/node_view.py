import pyqtgraph as pg
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QPainter, QPainterPath, QPicture
from PyQt6.QtWidgets import QStyleOptionGraphicsItem, QWidget

from res.constants import NODE_H_MARGIN, NODE_V_MARGIN
from ui.annotation.state.annotation_node_state import AnnotationNodeState


class NodeView(pg.GraphicsObject):
    def __init__(self, nodes: list[AnnotationNodeState], parent_plot: pg.PlotItem):
        super().__init__()
        self.nodes = nodes

        self.view_rect: QRectF = parent_plot.getViewBox().viewRect()
        self.setPos(self.view_rect.left(), self.view_rect.bottom())

        xs = [node.x for node in nodes]
        ys = [node.extents[0].tier for node in nodes]
        circle = pg.PlotDataItem(
            xs, ys, pen=None, symbol="o", symbolPen="b", symbolSize=8
        )
        circle.setParentItem(self)

        self.pic = QPicture()
        self._generate_picture()

    def _generate_picture(self):
        painter = QPainter(self.pic)

        solid_path = QPainterPath()
        dotted_path = QPainterPath()
        for node in self.nodes:
            self.prepareGeometryChange()
            started = False
            for extent in node.extents:
                y = extent.tier
                if started and solid_path.currentPosition().y() != y:
                    dotted_path.moveTo(node.x, solid_path.currentPosition().y())
                    dotted_path.lineTo(node.x, y)

                solid_path.moveTo(node.x, y)

                if extent.has_point_label:
                    solid_path.lineTo(node.x, y + 0.2)
                else:
                    solid_path.lineTo(node.x, y + 1)

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
        return self.view_rect.adjusted(
            -NODE_H_MARGIN, -NODE_V_MARGIN, NODE_H_MARGIN, NODE_V_MARGIN
        )
