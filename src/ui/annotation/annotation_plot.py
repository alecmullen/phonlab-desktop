import pyqtgraph as pg
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QWidget

from ui.annotation.annotation_state import AnnotationState
from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.annotation.component.label import Label
from ui.annotation.component.node import Node


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

        self.getViewBox().setXLink(linked_plot)
        self.getAxis("left").setWidth(60)

        self.getViewBox().setFlag(self.getViewBox().GraphicsItemFlag.ItemClipsChildrenToShape, False)

        if is_bottom_plot:
            self.setLabel("bottom", self.tr("Time"), units="s")
            self.getAxis("bottom").enableAutoSIPrefix(False)
        else:
            self.getAxis("bottom").setStyle(showValues=False)

        self.nodes: list[Node] = []
        self.labels: list[Label] = []
        self.populate(self.view_model.annotation_state)

        self.dragging_node: Node = None

    def connect_plot_signals(self):
        self.scene().sigMouseMoved.connect(self.on_mouse_moved)

    def show_time_axis(self, show: bool):
        if show:
            self.setLabel("bottom", self.tr("Time"), units="s")
            self.getAxis("bottom").enableAutoSIPrefix(False)

    def populate(self, annotation_state: AnnotationState):
        nodes = annotation_state.nodes
        types = annotation_state.types

        self.setYRange(-0.1, len(types), padding=0)
        self.getAxis("left").setTicks([[(i, type.type) for i, type in enumerate(types)]])
        label_height = self.getViewBox().viewRect().height() / (1.2 * len(types))

        node_extents = { node: set() for node in nodes }
        for i, type in enumerate(types):
            for label in type.labels:
                x_e = nodes[label.e_node]
                x_s = nodes[label.s_node]

                center_x = (x_e - x_s) / 2 + x_s
                center_y = i + 0.5
                width = (x_e - x_s)
                label_item = Label((width, label_height), label.label)
                label_item.setPos(center_x, center_y)
                self.labels.append(label_item)
                self.addItem(label_item)

                node_extents[label.e_node].add(i)
                node_extents[label.s_node].add(i)

        for node in nodes:
            node = Node(nodes[node], sorted(node_extents[node]))
            self.nodes.append(node)
            self.addItem(node)

    def handle_mouse_press(self, event):
        for node in self.nodes:
            child_pos = node.mapFromScene(event.position())
            if node.contains(child_pos):
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
            y = self.dragging_node.y()
            self.dragging_node.setPos(x, y)
