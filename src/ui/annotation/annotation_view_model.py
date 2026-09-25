from dataclasses import replace

from core.parse_textgrid.annotation import Annotation
from core.parse_textgrid.parse_textgrid import ParseTextGrid, ParseTextGridError
from ui.annotation.state.annotation_label_state import AnnotationLabelState
from ui.annotation.state.annotation_node_state import AnnotationNodeState
from ui.annotation.state.annotation_window_state import (
    AnnotationWindowState,
    to_annotation_window_state,
    update_annotation_window_state,
)
from ui.base.view_model import ViewModel
from ui.document.state.status_message_state import StatusMessageState


class AnnotationViewModel(ViewModel):
    def __init__(self):
        super().__init__()

        self.annotation_window_state = AnnotationWindowState()

    def change_node_state(self, drag_node: AnnotationNodeState, new_pos: float):
        start, end = (
            self.annotation_window_state.start,
            self.annotation_window_state.end,
        )
        annotation_state = self.annotation_window_state.annotation_state

        if new_pos < start or new_pos > end:
            return

        if not all(extent.has_point_label for extent in drag_node.extents):
            for node in annotation_state.nodes.values():
                if node.node == drag_node.node:
                    continue
                if node.x < drag_node.x and node.x >= new_pos:
                    new_pos = node.x
                if node.x > drag_node.x and node.x <= new_pos:
                    new_pos = node.x

        annotation_state.nodes[drag_node.node] = replace(
            annotation_state.nodes[drag_node.node], x=new_pos
        )

        self.annotation_window_state = replace(
            self.annotation_window_state, annotation_state=annotation_state
        )
        self.update_annotation_window_state()

    def set_annotation_state(self, annotation: Annotation):
        self.annotation_window_state = to_annotation_window_state(
            annotation,
            self.annotation_window_state.start,
            self.annotation_window_state.end,
        )
        self.state_changed.emit(self.annotation_window_state)

    def set_window_state(self, start: float, end: float):
        self.annotation_window_state = update_annotation_window_state(
            self.annotation_window_state.annotation_state, start, end
        )
        self.state_changed.emit(self.annotation_window_state)

    def update_annotation_window_state(self):
        self.annotation_window_state = update_annotation_window_state(
            self.annotation_window_state.annotation_state,
            self.annotation_window_state.start,
            self.annotation_window_state.end,
        )
        self.state_changed.emit(self.annotation_window_state)

    def select_label(self, label_view_state: AnnotationLabelState):
        pass

    def parse_textgrid(self, path: str):
        use_case = ParseTextGrid(path)
        try:
            annotation = use_case.invoke()
            self.set_annotation_state(annotation)
        except ParseTextGridError as e:
            self.state_changed.emit(StatusMessageState(str(e)))
