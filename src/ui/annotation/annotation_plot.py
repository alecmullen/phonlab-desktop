import pyqtgraph as pg
from PyQt6.QtCore import QPointF, Qt, QTimer, pyqtSlot
from PyQt6.QtGui import (
    QFocusEvent,
    QFont,
    QFontMetrics,
    QKeyEvent,
    QKeySequence,
    QShowEvent,
)
from PyQt6.QtWidgets import QGraphicsSceneMouseEvent, QWidget

from res.constants import LEFT_AXIS_WIDTH, NODE_H_MARGIN, NODE_V_MARGIN
from ui.annotation.annotation_view_model import AnnotationViewModel
from ui.annotation.component.label_view import LabelView
from ui.annotation.component.node_view import NodeView
from ui.annotation.component.tier_selection_indicator import TierSelectionIndicator
from ui.annotation.state.annotation_label_state import AnnotationLabelState
from ui.annotation.state.annotation_node_state import AnnotationNodeState
from ui.annotation.state.annotation_state import AnnotationState
from ui.base.state import State
from ui.common.context_menu_hint import ContextMenuHintAction
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
        self.set_up_menu()
        self.ctrlMenu.menuAction().setVisible(False)

        self.context_pos: QPointF | None = None

        self.visible_nodes: list[AnnotationNodeState] = []
        self.visible_labels: list[AnnotationLabelState] = []

        self.dragging_node: AnnotationNodeState | None = None
        self.selected_node: int | None = None

        self.selected_type: int | None = None

        self.tier_selection = TierSelectionIndicator(self)

        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def set_up_menu(self):
        shortcut = QKeySequence("Ctrl+L")
        create_label_action = ContextMenuHintAction(
            self.tr("Create Label"),
            shortcut.toString(QKeySequence.SequenceFormat.NativeText),
            parent=self,
        )
        create_label_action.setShortcut(shortcut)
        create_label_action.triggered.connect(self.create_label_from_selection)

        self.addAction(create_label_action)
        self.getViewBox().menu.addAction(create_label_action)
        self.getViewBox().menu.aboutToHide.connect(self.on_context_menu_about_to_close)

    @pyqtSlot()
    def on_context_menu_about_to_close(self):
        QTimer.singleShot(0, self.on_context_menu_close)

    @pyqtSlot()
    def on_context_menu_close(self):
        self.context_pos = None

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
        for item in self.allChildItems():
            if isinstance(item, (LabelView, NodeView)):
                self.removeItem(item)

    def populate(self, annotation_state: AnnotationState):
        self.clear_annotations()

        nodes = annotation_state.nodes
        types = annotation_state.types

        self.setYRange(-0.1, len(types), padding=0)

        font = self.getAxis("left").style.get("tickFont") or QFont()
        metrics = QFontMetrics(font)
        ticks = [
            (
                i,
                metrics.elidedText(
                    type.type, Qt.TextElideMode.ElideRight, LEFT_AXIS_WIDTH
                ),
            )
            for i, type in enumerate(types)
        ]
        self.getAxis("left").setTicks([ticks])

        self.visible_nodes = []
        self.visible_labels = []
        if len(types) == 0:
            return

        for type in types:
            self.visible_labels += [label for label in type.labels if label.is_visible]

        label_view = LabelView(self, self.visible_labels, self.on_label_edit)
        label_view.setPos(0, 0)
        self.addItem(label_view)

        self.visible_nodes = [node for node in nodes.values() if node.is_visible]

        node_view = NodeView(self, self.visible_nodes, self.selected_node)
        node_view.setPos(0, 0)
        self.addItem(node_view)

    def unselect_node(self):
        self.selected_node = None
        node_view = next(
            item for item in self.allChildItems() if isinstance(item, NodeView)
        )
        node_view.set_selected_node(None)

    def mousePressEvent(self, a0: QGraphicsSceneMouseEvent | None):
        if a0 is None:
            return

        pos = self.getViewBox().mapSceneToView(a0.scenePos())

        if a0.button() == Qt.MouseButton.RightButton:
            self.context_pos = pos
            a0.ignore()
            return

        pixel_size = self.getViewBox().viewPixelSize()
        h_margin = NODE_H_MARGIN * pixel_size[0]
        v_margin = NODE_V_MARGIN * pixel_size[1]

        for node_view_state in self.visible_nodes:
            node_x = node_view_state.x
            node_y = node_view_state.extents[0].tier
            if abs(pos.x() - node_x) < h_margin and abs(pos.y() - node_y) < v_margin:
                self.dragging_node = node_view_state
                a0.accept()
                return

        a0.ignore()

    def mouseReleaseEvent(self, a0: QGraphicsSceneMouseEvent | None):
        if a0 is None:
            return
        if self.dragging_node is not None:
            self.selected_node = self.dragging_node.node
            self.dragging_node = None
            self.populate(self.view_model.annotation_view_state)
            a0.accept()
        else:
            a0.ignore()

    def focusOutEvent(self, a0: QFocusEvent | None):
        if a0 is not None:
            if self.selected_node is not None:
                self.unselect_node()
            a0.ignore()

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

    def keyPressEvent(self, a0: QKeyEvent | None):
        if a0 is None:
            return
        if (
            a0.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace)
            and self.selected_node is not None
        ):
            self.view_model.delete_node(self.selected_node)
            a0.accept()
        else:
            a0.ignore()

    @pyqtSlot(int, str)
    def on_label_edit(self, label_id: int, text: str):
        self.view_model.change_label_text(label_id, text)

    @pyqtSlot(object)
    def on_mouse_moved(self, pos: QPointF):
        scene_pos = self.getViewBox().mapSceneToView(pos)
        x, y = scene_pos.x(), scene_pos.y()

        if self.dragging_node is not None:
            self.view_model.change_node_state(self.dragging_node, x)

        if not self.viewRect().contains(scene_pos):
            self.selected_type = None
        else:
            self.selected_type = int(y)

        self.update_selected_type()

        super().on_mouse_moved(pos)

    def update_selected_type(self):
        if self.selected_type is None:
            self.tier_selection.set_visible(False)
        elif self.selection_region.isVisible():
            start, end = self.selection_region.getRegion()
            self.tier_selection.set_boundaries(self.selected_type, start, end)

    def create_label_from_selection(self):
        if not self.selection_region.isVisible():
            return

        if self.context_pos is not None:
            type = int(self.context_pos.y())
        elif self.selected_type is not None:
            type = self.selected_type
        else:
            return

        start, end = self.selection_region.getRegion()
        self.view_model.create_label_from_selection(type, start, end)
