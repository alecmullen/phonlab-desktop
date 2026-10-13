import pyqtgraph as pg
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QPainter, QPainterPath, QPicture
from PyQt6.QtWidgets import QStyleOptionGraphicsItem, QWidget

from res.constants import NODE_H_MARGIN, NODE_V_MARGIN
from ui.annotation.state.annotation_node_state import AnnotationNodeState


class NodeView(pg.GraphicsObject):
    def __init__(
        self,
        parent_plot: pg.PlotItem,
        nodes: list[AnnotationNodeState],
        selected_node: int | None = None,
    ):
        super().__init__()
        self.nodes = nodes
        self.selected_node = selected_node

        self.view_rect: QRectF = parent_plot.getViewBox().viewRect()
        self.setPos(self.view_rect.left(), self.view_rect.bottom())

        blue_xs = []
        blue_ys = []
        red_xs = []
        red_ys = []

        for node in nodes:
            if node.node != self.selected_node:
                blue_xs.append(node.x)
                blue_ys.append(node.extents[0].tier)
            else:
                red_xs.append(node.x)
                red_ys.append(node.extents[0].tier)

        self._plot_circles(blue_xs, blue_ys, "b")
        if len(red_xs) > 0:
            self._plot_circles(red_xs, red_ys, "r")

        self.pic = QPicture()
        self._generate_picture()

    def _plot_circles(self, xs: list[float], ys: list[int], color: str):
        circles = pg.PlotDataItem(
            xs,
            ys,
            pen=None,
            symbol="o",
            symbolPen=color,
            symbolBrush=color,
            symbolSize=8,
        )
        circles.setParentItem(self)

    def _generate_picture(self):
        painter = QPainter(self.pic)

        solid_path_blue = QPainterPath()
        dotted_path_blue = QPainterPath()
        solid_path_red = QPainterPath()
        dotted_path_red = QPainterPath()

        for node in self.nodes:
            self.prepareGeometryChange()
            started = False
            if node.node == self.selected_node:
                solid_path = solid_path_red
                dotted_path = dotted_path_red
            else:
                solid_path = solid_path_blue
                dotted_path = dotted_path_blue
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

        for solid_path, dotted_path, color in [
            (solid_path_blue, dotted_path_blue, "b"),
            (solid_path_red, dotted_path_red, "r"),
        ]:
            pen = pg.mkPen(color=color, width=3)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

            painter.setPen(pen)
            painter.drawPath(solid_path)

            pen = pg.mkPen(color=color, width=3)
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
