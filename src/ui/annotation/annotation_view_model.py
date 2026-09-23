from dataclasses import replace

from ui.annotation.annotation_window_state import AnnotationWindowState
from ui.annotation.state.node_view_state import NodeViewState
from ui.base.view_model import ViewModel


class AnnotationViewModel(ViewModel):
    def __init__(self):
        super().__init__()

        self.annotation_window_state = AnnotationWindowState()

    def change_node_state(self, drag_node: NodeViewState, new_pos: float):
        start, end = (
            self.annotation_window_state.start,
            self.annotation_window_state.end,
        )
        annotation_state = self.annotation_window_state.annotation_state

        if new_pos < start or new_pos > end:
            return

        if not all(extent.has_point_label for extent in drag_node.extents):
            for node, x in annotation_state.nodes.items():
                if node == drag_node.node:
                    continue
                if x < drag_node.x and x >= new_pos:
                    new_pos = x
                if x > drag_node.x and x <= new_pos:
                    new_pos = x

        annotation_state.nodes[drag_node.node] = new_pos

        self.annotation_window_state = replace(
            self.annotation_window_state, annotation_state=annotation_state
        )
        self.state_changed.emit(self.annotation_window_state)

    def set_annotation_state(self, state: AnnotationWindowState):
        self.annotation_window_state = state
        self.state_changed.emit(self.annotation_window_state)
