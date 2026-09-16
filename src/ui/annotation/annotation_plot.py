import pyqtgraph as pg
from PyQt6.QtCore import QPointF, Qt, pyqtSlot
from PyQt6.QtGui import QMouseEvent, QShowEvent
from PyQt6.QtWidgets import QWidget

from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.annotation.annotation_window_state import AnnotationWindowState
from ui.annotation.component.label_view import LabelView
from ui.annotation.component.node_view import NodeView
from ui.annotation.state.label_view_state import LabelViewState
from ui.annotation.state.node_view_state import NodeViewState
from ui.base.state import State
from ui.common.cursor_controller import CursorController

V_MARGIN = 7
H_MARGIN = 5


class AnnotationPlot(pg.PlotItem, CursorController):
    def __init__(
        self,
        view_model: AnnotationViewModel,
        linked_plot: pg.PlotItem | None = None,
        is_bottom_plot: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self.view_model = view_model
        self.view_model.subscribe(self.on_state_change)

        if linked_plot is not None:
            self.getViewBox().setXLink(linked_plot)
        self.getAxis("left").setWidth(60)

        self.getViewBox().setFlag(
            self.getViewBox().GraphicsItemFlag.ItemClipsChildrenToShape, False
        )

        self.cursor_line = pg.InfiniteLine(angle=90, movable=False, pen="r")
        self.addItem(self.cursor_line, ignoreBounds=True)

        if is_bottom_plot:
            self.setLabel("bottom", self.tr("Time"), units="s")
            self.getAxis("bottom").enableAutoSIPrefix(False)
        else:
            self.getAxis("bottom").setStyle(showValues=False)

        self.getViewBox().menu.clear()
        self.ctrlMenu.menuAction().setVisible(False)

        self.mark_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(color="g", width=2, style=Qt.PenStyle.DashLine),
        )
        self.addItem(self.mark_line, ignoreBounds=True)
        self.mark_line.setVisible(False)

        self.visible_nodes: dict[int, NodeViewState] = {}

        self.dragging_node: int | None = None

    @pyqtSlot(object)
    def on_state_change(self, model: State):
        if isinstance(model, AnnotationWindowState):
            self.populate(model)

    def show_time_axis(self, show: bool):
        if show:
            self.setLabel("bottom", self.tr("Time"), units="s")
            self.getAxis("bottom").enableAutoSIPrefix(False)

    def showEvent(self, a0: QShowEvent):
        super().showEvent(a0)
        self.populate(self.view_model.annotation_window_state)

    def populate(self, window_state: AnnotationWindowState):
        self.clear()

        nodes = window_state.annotation_state.nodes
        types = window_state.annotation_state.types
        start = window_state.start
        end = window_state.end

        self.setYRange(-0.1, len(types), padding=0)
        self.getAxis("left").setTicks(
            [[(i, type.type) for i, type in enumerate(types)]]
        )

        if len(types) == 0:
            return

        label_height = self.getViewBox().viewRect().height() / (1.2 * len(types))
        node_extents = {node: set() for node in nodes}
        for i, type in enumerate(types):
            label_view_states = []
            for label in type.labels:
                if nodes[label.e_node] <= start or nodes[label.s_node] >= end:
                    continue
                x_s = max(start, nodes[label.s_node])
                x_e = min(end, nodes[label.e_node])

                center_x = (x_e - x_s) / 2 + x_s
                center_y = i + 0.5
                width = x_e - x_s

                label_view_states.append(
                    LabelViewState(
                        (width, label_height), (center_x, center_y), label.label
                    )
                )

                node_extents[label.e_node].add(i)
                node_extents[label.s_node].add(i)
            label_view = LabelView(label_view_states, self)
            label_view.setPos(0, 0)
            self.addItem(label_view)

        self.visible_nodes = {}
        for node, loc in nodes.items():
            if start <= loc <= end:
                self.visible_nodes[node] = NodeViewState(
                    loc, sorted(node_extents[node])
                )
        node_view = NodeView(list(self.visible_nodes.values()), self)
        node_view.setPos(0, 0)
        self.addItem(node_view)

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        pixel_size = self.getViewBox().viewPixelSize()
        h_margin = H_MARGIN * pixel_size[0]
        v_margin = V_MARGIN * pixel_size[1]

        pos = self.getViewBox().mapSceneToView(event.position())

        for node, node_view_state in self.visible_nodes.items():
            node_x = node_view_state.x
            node_y = node_view_state.ys[0]
            if abs(pos.x() - node_x) < h_margin and abs(pos.y() - node_y) < v_margin:
                self.dragging_node = node
                event.accept()
                return True
        return False

    def handle_mouse_release(self, event: QMouseEvent) -> bool:
        if self.dragging_node is not None:
            self.dragging_node = None
            event.accept()
            return True
        return False

    @pyqtSlot(object)
    def on_mouse_moved(self, pos: QPointF):
        x = self.getViewBox().mapSceneToView(pos).x()

        if self.dragging_node is not None:
            self.view_model.change_node_state(self.dragging_node, x)
        elif self.has_cursor_control:
            self.cursor_line.setPos(x)

    def set_cursor_position(self, x: float):
        self.remove_cursor_control()
        self.cursor_line.setPos(x)

    def set_mark_position(self, x: float, visible: bool):
        self.mark_line.setPos(x)
        self.mark_line.setVisible(visible)
