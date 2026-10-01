import pyqtgraph as pg
from PyQt6.QtCore import QPointF, pyqtSlot
from PyQt6.QtGui import QMouseEvent, QShowEvent
from PyQt6.QtWidgets import QWidget

from res.constants import NODE_H_MARGIN, NODE_V_MARGIN
from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.annotation.component.label_view import LabelView
from ui.annotation.component.node_view import NodeView
from ui.annotation.state.annotation_label_state import AnnotationLabelState
from ui.annotation.state.annotation_node_state import AnnotationNodeState
from ui.annotation.state.annotation_state import AnnotationState
from ui.base.state import State
from ui.common.document_plot import DocumentPlot


class AnnotationPlot(DocumentPlot):
    def __init__(
        self,
        view_model: AnnotationViewModel,
        linked_plot: pg.PlotItem | None = None,
        is_bottom_plot: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent, linked_plot, is_bottom_plot)

        self.view_model = view_model
        self.view_model.subscribe(self.on_state_change)

        self.showAxis("top", True)
        self.getAxis("top").setTicks([])

        self.getViewBox().menu.clear()
        self.ctrlMenu.menuAction().setVisible(False)

        self.visible_nodes: list[AnnotationNodeState] = []
        self.visible_labels: list[AnnotationLabelState] = []

        self.node_view: NodeView | None = None
        self.label_view: LabelView | None = None

        self.dragging_node: AnnotationNodeState | None = None

    @pyqtSlot(object)
    def on_state_change(self, model: State):
        if isinstance(model, AnnotationState):
            self.populate(model)

    def show_time_axis(self, show: bool):
        if show:
            self.setLabel("bottom", self.tr("Time"), units="s")
            self.getAxis("bottom").enableAutoSIPrefix(False)

    def showEvent(self, a0: QShowEvent):
        super().showEvent(a0)
        self.populate(self.view_model.annotation_view_state)

    def clear_annotations(self):
        node_view = self.node_view
        label_view = self.label_view
        self.node_view = None
        self.label_view = None
        if node_view is not None:
            self.removeItem(node_view)
        if label_view is not None:
            self.removeItem(label_view)

    def populate(self, annotation_state: AnnotationState):
        self.clear_annotations()

        nodes = annotation_state.nodes
        types = annotation_state.types

        self.setYRange(-0.1, len(types), padding=0)
        self.getAxis("left").setTicks(
            [[(i, type.type) for i, type in enumerate(types)]]
        )

        self.visible_nodes = []
        self.visible_labels = []
        if len(types) == 0:
            return

        for type in types:
            self.visible_labels += [label for label in type.labels if label.is_visible]

        self.label_view = LabelView(self.visible_labels, self)
        self.label_view.setPos(0, 0)
        self.addItem(self.label_view)

        self.visible_nodes = [node for node in nodes.values() if node.is_visible]

        self.node_view = NodeView(self.visible_nodes, self)
        self.node_view.setPos(0, 0)
        self.addItem(self.node_view)

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        pixel_size = self.getViewBox().viewPixelSize()
        h_margin = NODE_H_MARGIN * pixel_size[0]
        v_margin = NODE_V_MARGIN * pixel_size[1]

        pos = self.getViewBox().mapSceneToView(event.position())

        for node_view_state in self.visible_nodes:
            node_x = node_view_state.x
            node_y = node_view_state.extents[0].tier
            if abs(pos.x() - node_x) < h_margin and abs(pos.y() - node_y) < v_margin:
                self.dragging_node = node_view_state
                return True
        return False

    def handle_mouse_release(self, event: QMouseEvent) -> bool:
        if self.dragging_node is not None:
            self.dragging_node = None
            event.accept()
            return True

        return False

    def handle_single_click(self, scene_pos: QPointF) -> bool:
        pos = self.getViewBox().mapSceneToView(scene_pos)
        for label_view_state in self.visible_labels:
            label_pos, label_size = label_view_state.pos, label_view_state.size
            if (
                abs(pos.x() - label_pos[0]) < label_size[0] / 2
                and abs(pos.y() - label_pos[1]) < label_size[1] / 2
            ):
                self.view_model.select_label(label_view_state)
                return True
        return False

    @pyqtSlot(object)
    def on_mouse_moved(self, pos: QPointF):
        x = self.getViewBox().mapSceneToView(pos).x()

        if self.dragging_node is not None:
            self.view_model.change_node_state(self.dragging_node, x)

        super().on_mouse_moved(pos)
