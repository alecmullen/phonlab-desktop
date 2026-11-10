import pyqtgraph as pg
from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QStyleOptionGraphicsItem, QWidget


class LoadingOverlay(pg.GraphicsObject):
    """A semi-transparent overlay with an animated spinner, covering the plot's view box."""

    SPINNER_SIZE = 40

    def __init__(self, parent_plot: pg.PlotItem):
        super().__init__()
        self.angle = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)

        self.view_box = parent_plot.getViewBox()
        self.setParentItem(self.view_box)
        self.setZValue(1000)
        self.setVisible(False)

        self.view_box.sigResized.connect(self.on_view_box_resized)

    def on_view_box_resized(self):
        self.prepareGeometryChange()
        self.update()

    def rotate(self):
        self.angle = (self.angle + 10) % 360
        self.update()

    def show(self):
        self.timer.start(30)
        self.setVisible(True)

    def hide(self):
        self.timer.stop()
        self.setVisible(False)

    def paint(
        self,
        painter: QPainter | None,
        option: QStyleOptionGraphicsItem | None,
        widget: QWidget | None,
    ):
        if painter is None:
            return

        view_rect = self.boundingRect()

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Draw a semi-transparent dark backdrop over the graph
        painter.fillRect(view_rect, QColor(0, 0, 0, 20))

        # 2. Draw the spinning arc
        width = view_rect.width()
        height = view_rect.height()
        spinner_size = self.SPINNER_SIZE

        # Center the spinner
        rect = QRectF(
            (width - spinner_size) / 2,
            (height - spinner_size) / 2,
            spinner_size,
            spinner_size,
        )

        pen = QPen(QColor(0, 0, 255, 160))
        pen.setWidth(6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        # Draw a 270-degree arc that rotates over time
        # Qt measures angles in 1/16th of a degree
        painter.drawArc(rect, -self.angle * 16, 270 * 16)

    def boundingRect(self) -> QRectF:
        return self.view_box.boundingRect()
