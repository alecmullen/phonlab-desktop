import pyqtgraph as pg
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QWidget

from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.annotation.annotation_window_state import AnnotationWindowState
from ui.annotation.component.label_view import LabelView
from ui.annotation.component.node_view import NodeView
from ui.document.state.annotation_state import AnnotationState


class AnnotationPlot(pg.PlotItem):
    def __init__(
        self,
        parent: QWidget | None = None,
        view_model: AnnotationViewModel = None,
        linked_plot: pg.PlotItem | None = None,
        is_bottom_plot: bool = False
    ):
        super().__init__(parent)

        self.view_model = view_model
        self.view_model.subscribe(self.on_state_change)

        self.getViewBox().setXLink(linked_plot)
        self.getAxis("left").setWidth(60)

        self.getViewBox().setFlag(self.getViewBox().GraphicsItemFlag.ItemClipsChildrenToShape, False)

        if is_bottom_plot:
            self.setLabel("bottom", self.tr("Time"), units="s")
            self.getAxis("bottom").enableAutoSIPrefix(False)
        else:
            self.getAxis("bottom").setStyle(showValues=False)

        self.node_views: dict[int, NodeView] = {}
        self.label_views: list[LabelView] = []

        self.dragging_node: int = None

        self.populate(self.view_model.annotation_window_state)

    @pyqtSlot(object)
    def on_state_change(self, model):
        if isinstance(model, AnnotationWindowState):
            self.populate(model)

    def connect_plot_signals(self):
        self.scene().sigMouseMoved.connect(self.on_mouse_moved)

    def show_time_axis(self, show: bool):
        if show:
            self.setLabel("bottom", self.tr("Time"), units="s")
            self.getAxis("bottom").enableAutoSIPrefix(False)

    def populate(self, window_state: AnnotationWindowState):
        self.clear()

        nodes = window_state.annotation_state.nodes
        types = window_state.annotation_state.types
        start = window_state.start
        end = window_state.end

        self.setYRange(-0.1, len(types), padding=0)
        self.getAxis("left").setTicks([[(i, type.type) for i, type in enumerate(types)]])
        label_height = self.getViewBox().viewRect().height() / (1.2 * len(types))

        node_extents = { node: set() for node in nodes }
        for i, type in enumerate(types):
            for label in type.labels:
                if nodes[label.e_node] < start or nodes[label.s_node] > end:
                    return
                x_e = max(start, nodes[label.e_node])
                x_s = min(end, nodes[label.s_node])

                center_x = (x_e - x_s) / 2 + x_s
                center_y = i + 0.5
                width = (x_e - x_s)
                label_item = LabelView((width, label_height), label.label)
                label_item.setPos(center_x, center_y)
                self.label_views.append(label_item)
                self.addItem(label_item)

                node_extents[label.e_node].add(i)
                node_extents[label.s_node].add(i)

        for node in nodes:
            if start < nodes[node] < end:
                node_view = NodeView(nodes[node], sorted(node_extents[node]))
                self.node_views[node] = node_view
                self.addItem(node_view)

    def handle_mouse_press(self, event):
        for node, node_view in self.node_views.items():
            child_pos = node_view.mapFromScene(event.position())
            if node_view.contains(child_pos):
                self.dragging_node = node
                event.accept()
                return True
        return False

    def handle_mouse_release(self, event):
        if self.dragging_node is not None:
            self.dragging_node = None
            event.accept()
            return True
        return False

    @pyqtSlot(object)
    def on_mouse_moved(self, pos):
        if self.dragging_node is not None:
            x = self.getViewBox().mapSceneToView(pos).x()
            self.view_model.change_node_state(self.dragging_node, x)
