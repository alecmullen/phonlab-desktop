from dataclasses import replace

from ui.annotation.annotation_window_state import AnnotationWindowState
from ui.base.view_model import ViewModel


class AnnotationViewModel(ViewModel):
    def __init__(self):
        super().__init__()

        self.annotation_window_state: AnnotationWindowState = None

    def change_node_state(self, drag_node: int, new_pos: float):
        start, end = (
            self.annotation_window_state.start,
            self.annotation_window_state.end,
        )
        annotation_state = self.annotation_window_state.annotation_state

        if new_pos < start or new_pos > end:
            return

        annotation_state.nodes[drag_node] = new_pos
        for node, x in annotation_state.nodes.items():
            if node < drag_node and x >= new_pos:
                annotation_state.nodes[node] = new_pos
            if node > drag_node and x <= new_pos:
                annotation_state.nodes[node] = new_pos

        self.annotation_window_state = replace(
            self.annotation_window_state, annotation_state=annotation_state
        )
        self.state_changed.emit(self.annotation_window_state)

    def set_annotation_state(self, state: AnnotationWindowState):
        self.annotation_window_state = state
        self.state_changed.emit(self.annotation_window_state)
