import pyqtgraph as pg
from PyQt6.QtCore import QPointF, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import QWidget

from res.constants import LEFT_AXIS_WIDTH


class DocumentPlot(pg.PlotItem):
    """Plot to be used in DocumentView with a shared time axis. Handles
    time cursor, interval selection, and time mark UI items"""

    def __init__(
        self,
        parent: QWidget | None = None,
        linked_plot: pg.PlotItem | None = None,
        is_bottom_plot: bool = False,
    ):
        super().__init__(parent)
        self.has_cursor_control = True

        self.cursor_control_timer = QTimer()
        self.cursor_control_timer.setInterval(150)
        self.cursor_control_timer.setSingleShot(True)
        self.cursor_control_timer.timeout.connect(self.regain_cursor_control)

        self.cursor_line = pg.InfiniteLine(angle=90, movable=False, pen="r")
        self.cursor_line.setZValue(10)
        self.addItem(self.cursor_line, ignoreBounds=True)

        self.mark_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(color="g", width=2, style=Qt.PenStyle.DashLine),
        )
        self.mark_line.setVisible(False)
        self.mark_line.setZValue(10)
        self.addItem(self.mark_line, ignoreBounds=True)

        self.selection_region = pg.LinearRegionItem(
            values=[0, 0],
            brush=pg.mkBrush(0, 100, 200, 50),
            movable=False,
        )
        self.selection_region.setZValue(10)
        self.addItem(self.selection_region)
        self.selection_region.setVisible(False)

        self.vb.setMouseEnabled(x=False, y=False)
        self.vb.rbScaleBox.hide()
        self.getAxis("left").setWidth(LEFT_AXIS_WIDTH)

        if linked_plot is not None:
            self.getViewBox().setXLink(linked_plot)

        if is_bottom_plot:
            self.setLabel("bottom", self.tr("Time"), units="s")
            self.getAxis("bottom").enableAutoSIPrefix(False)
        else:
            self.getAxis("bottom").setStyle(showValues=False)

    @pyqtSlot()
    def regain_cursor_control(self):
        self.has_cursor_control = True

    def remove_cursor_control(self):
        self.has_cursor_control = False
        self.cursor_control_timer.start()

    def set_cursor_position(self, x: float):
        self.remove_cursor_control()
        self.cursor_line.setPos(x)

    @pyqtSlot(object)
    def on_mouse_moved(self, pos: QPointF):
        if self.has_cursor_control:
            x = self.getViewBox().mapSceneToView(pos).x()
            self.cursor_line.setPos(x)

    def set_mark_position(self, x: float, visible: bool):
        self.mark_line.setPos(x)
        self.mark_line.setVisible(visible)

    def update_selection_region(self, box_left: float, xrange: float):
        if xrange > 0:
            self.selection_region.setRegion([box_left, box_left + xrange])
            self.selection_region.setVisible(True)
        else:
            self.selection_region.setVisible(False)
